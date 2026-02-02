"""BigQuery client with connection pooling and query building.

Unified BigQuery client supporting both crypto and gold market data.
"""

import asyncio
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from google.cloud import bigquery
from google.cloud.bigquery import Client as BigQueryClientBase
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings, get_settings
from .exceptions import BigQueryError
from .logging import get_logger

logger = get_logger(__name__)


class BigQueryClient:
    """BigQuery client wrapper with async support and multi-market support.
    
    Uses unified single dataset architecture (Option A) with Terraform table names.
    """

    # Terraform table names (single dataset architecture)
    RAW_DATA_TABLE = "raw_data"  # Bronze layer - raw ingested events
    SENTIMENT_ANALYSIS_TABLE = "sentiment_analysis"  # Silver layer - processed sentiment events
    MARKET_CONTEXT_TABLE = "market_context"  # Silver layer - market indicators
    PREDICTIONS_TABLE = "predictions"  # Gold layer - AI/ML predictions
    PREDICTION_ACCURACY_TABLE = "prediction_accuracy"  # Gold layer - validation results
    ALERTS_TABLE = "alerts"  # Gold layer - alert notifications
    ANALYTICS_SUMMARY_TABLE = "analytics_summary"  # Gold layer - daily aggregated analytics

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.project_id = self.settings.google_cloud_project or self.settings.pubsub_project_id
        self.dataset = self.settings.bigquery_dataset  # Single unified dataset
        self._client: Optional[BigQueryClientBase] = None
        
    # Backward compatibility aliases for dataset references
    @property
    def bronze_dataset(self) -> str:
        """Backward compatibility - all data is in the unified dataset."""
        return self.dataset
    
    @property
    def silver_dataset(self) -> str:
        """Backward compatibility - all data is in the unified dataset."""
        return self.dataset
    
    @property
    def gold_dataset(self) -> str:
        """Backward compatibility - all data is in the unified dataset."""
        return self.dataset

    @property
    def client(self) -> BigQueryClientBase:
        """Get or create BigQuery client."""
        if self._client is None:
            if self.settings.bigquery_emulator_host:
                import os
                os.environ["BIGQUERY_EMULATOR_HOST"] = self.settings.bigquery_emulator_host
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    def _get_table_ref(self, dataset: str, table: str) -> str:
        """Get fully qualified table reference."""
        return f"{self.project_id}.{dataset}.{table}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def execute_query(
        self,
        query: str,
        parameters: Optional[list[Any]] = None,
        job_config: Optional[bigquery.QueryJobConfig] = None,
    ) -> bigquery.table.RowIterator:
        """Execute a query and return results."""
        try:
            if job_config is None:
                job_config = bigquery.QueryJobConfig()

            if parameters:
                job_config.query_parameters = parameters

            # Cost protection
            if self.settings.bigquery_max_bytes_billed > 0:
                job_config.maximum_bytes_billed = self.settings.bigquery_max_bytes_billed
                logger.debug(
                    "Query cost protection active",
                    max_bytes_billed=self.settings.bigquery_max_bytes_billed,
                )

            def _execute():
                query_job = self.client.query(query, job_config=job_config)
                return query_job.result()

            results = await asyncio.to_thread(_execute)
            logger.debug(
                "Query executed",
                query=query[:100],
                rows=results.total_rows,
            )
            return results
        except Exception as e:
            logger.error("Query failed", query=query[:100], error=str(e))
            raise BigQueryError(f"Query failed: {e}")

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        """Convert BigQuery Row into a plain dict."""
        try:
            return dict(row)
        except Exception:
            try:
                keys = list(row.keys())
                return {k: row[k] for k in keys}
            except Exception:
                return {"_row": row}

    async def query(
        self,
        query: str,
        parameters: Optional[list[Any]] = None,
        job_config: Optional[bigquery.QueryJobConfig] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async generator over query results as dicts."""
        results = await self.execute_query(query, parameters=parameters, job_config=job_config)
        for row in results:
            yield self._row_to_dict(row)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def insert_rows(
        self,
        dataset: str,
        table: str,
        rows: list[dict[str, Any]],
        row_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """Insert rows into a table."""
        if not rows:
            return []

        table_ref = self._get_table_ref(dataset, table)

        try:
            def _insert():
                return self.client.insert_rows_json(table_ref, rows, row_ids=row_ids)

            errors = await asyncio.to_thread(_insert)
            if errors:
                logger.error(
                    "Insert errors",
                    table=table_ref,
                    error_count=len(errors),
                    first_error=errors[0] if errors else None,
                )
            else:
                logger.debug(
                    "Rows inserted",
                    table=table_ref,
                    count=len(rows),
                )
            return list(errors) if errors else []
        except Exception as e:
            logger.error("Insert failed", table=table_ref, error=str(e))
            raise BigQueryError(f"Insert failed for {table_ref}: {e}")

    async def insert_raw_event(self, event: dict[str, Any], market_type: Optional[str] = None) -> None:
        """Insert a raw event into raw_data table (bronze layer)."""
        row = self._serialize_datetimes(event)

        # Add market type if provided
        if market_type and "market_type" not in row:
            row["market_type"] = market_type

        # BigQuery JSON columns require JSON-typed values
        for k in ("payload", "metadata"):
            if k in row and isinstance(row[k], (dict, list)):
                row[k] = json.dumps(row[k], ensure_ascii=False, separators=(",", ":"))

        row_id = str(row.get("event_id") or "")
        errors = await self.insert_rows(
            self.dataset,
            self.RAW_DATA_TABLE,
            [row],
            row_ids=[row_id] if row_id else None,
        )
        if errors:
            raise BigQueryError(f"Failed to insert raw event: {errors}")

    async def insert_processed_event(self, event: dict[str, Any], market_type: Optional[str] = None) -> None:
        """Insert a processed event into sentiment_analysis table (silver layer)."""
        row = self._serialize_datetimes(event)
        
        if market_type and "market_type" not in row:
            row["market_type"] = market_type
            
        row_id = str(row.get("event_id") or "")
        errors = await self.insert_rows(
            self.dataset,
            self.SENTIMENT_ANALYSIS_TABLE,
            [row],
            row_ids=[row_id] if row_id else None,
        )
        if errors:
            raise BigQueryError(f"Failed to insert processed event: {errors}")

    async def insert_alert(self, alert: dict[str, Any]) -> None:
        """Insert an alert into gold layer."""
        row = self._serialize_datetimes(alert)

        if "data" in row and isinstance(row["data"], (dict, list)):
            row["data"] = json.dumps(row["data"], ensure_ascii=False, separators=(",", ":"))

        row_id = str(row.get("alert_id") or "")
        errors = await self.insert_rows(
            self.gold_dataset,
            self.ALERTS_TABLE,
            [row],
            row_ids=[row_id] if row_id else None,
        )
        if errors:
            raise BigQueryError(f"Failed to insert alert: {errors}")

    def _serialize_datetimes(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert datetime objects to ISO format strings."""
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_datetimes(value)
            elif isinstance(value, list):
                result[key] = [
                    item.isoformat() if isinstance(item, datetime) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    async def query_sentiment_by_symbol(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        tenant_id: Optional[str] = None,
        market_type: Optional[str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Query sentiment data for a symbol."""
        # Build query dynamically
        base_query = """
            SELECT
                event_id,
                source,
                market_type,
                sentiment.score as sentiment_score,
                sentiment.label as sentiment_label,
                sentiment.confidence as confidence,
                symbols,
                processed_at
            FROM `{table}`
            WHERE @symbol IN UNNEST(symbols)
            AND processed_at BETWEEN @start_time AND @end_time
        """
        
        table_ref = self._get_table_ref(self.dataset, self.SENTIMENT_ANALYSIS_TABLE)
        query = base_query.format(table=table_ref)
        
        if tenant_id:
            query += " AND tenant_id = @tenant_id"
        if market_type:
            query += " AND market_type = @market_type"
        query += " ORDER BY processed_at DESC"

        parameters = [
            bigquery.ScalarQueryParameter("symbol", "STRING", symbol),
            bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
            bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
        ]

        if tenant_id:
            parameters.append(bigquery.ScalarQueryParameter("tenant_id", "STRING", tenant_id))
        if market_type:
            parameters.append(bigquery.ScalarQueryParameter("market_type", "STRING", market_type))

        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        results = await self.execute_query(query, job_config=job_config)

        for row in results:
            yield dict(row)

    async def get_sentiment_aggregation(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "HOUR",
        market_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get aggregated sentiment by time interval."""
        base_query = """
            SELECT
                TIMESTAMP_TRUNC(processed_at, {interval}) as time_bucket,
                AVG(sentiment.score) as avg_sentiment,
                COUNT(*) as event_count,
                AVG(sentiment.confidence) as avg_confidence,
                ARRAY_AGG(DISTINCT source) as sources
            FROM `{table}`
            WHERE @symbol IN UNNEST(symbols)
            AND processed_at BETWEEN @start_time AND @end_time
        """
        
        table_ref = self._get_table_ref(self.dataset, self.SENTIMENT_ANALYSIS_TABLE)
        query = base_query.format(interval=interval, table=table_ref)
        
        if market_type:
            query += " AND market_type = @market_type"
        query += " GROUP BY time_bucket ORDER BY time_bucket DESC"

        parameters = [
            bigquery.ScalarQueryParameter("symbol", "STRING", symbol),
            bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
            bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
        ]

        if market_type:
            parameters.append(bigquery.ScalarQueryParameter("market_type", "STRING", market_type))

        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        results = await self.execute_query(query, job_config=job_config)

        return [dict(row) for row in results]

    def close(self) -> None:
        """Close client connection."""
        if self._client:
            self._client.close()
            self._client = None
        logger.debug("BigQuery client closed")

    async def __aenter__(self) -> "BigQueryClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.close()
