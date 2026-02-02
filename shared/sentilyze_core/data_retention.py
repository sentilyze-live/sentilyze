"""Data retention and archival utilities for BigQuery.

This module handles:
- Automatic archiving of old data
- Partition management
- Cost optimization by moving cold data to cheaper storage
- Data deletion policies

Supports both crypto and gold market data with configurable retention periods.
Uses single unified dataset architecture.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from google.cloud import bigquery

from .config import get_settings
from .exceptions import BigQueryError
from .logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DataRetentionManager:
    """Manages data retention policies for BigQuery datasets.

    Implements tiered storage strategy with single unified dataset:
    - Hot data (0-30 days): Primary tables, full performance
    - Warm data (31-90 days): Partitioned tables, standard storage
    - Cold data (90+ days): Archived tables, long-term storage

    Tables in unified dataset:
    - raw_data: Bronze layer (raw ingested events)
    - sentiment_analysis: Silver layer (processed events)
    - market_context: Silver layer (market indicators)
    - predictions: Gold layer (AI/ML predictions)
    - prediction_accuracy: Gold layer (validation results)
    - alerts: Gold layer (alert notifications)
    - analytics_summary: Gold layer (aggregated analytics)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset: Optional[str] = None,
    ):
        self.project_id = project_id or settings.google_cloud_project
        self.dataset = dataset or settings.bigquery_dataset
        self.client: Optional[bigquery.Client] = None

    async def initialize(self) -> None:
        """Initialize BigQuery client."""
        if settings.bigquery_emulator_host:
            import os
            os.environ["BIGQUERY_EMULATOR_HOST"] = settings.bigquery_emulator_host
        self.client = bigquery.Client(project=self.project_id)
        logger.info("DataRetentionManager initialized", dataset=self.dataset)

    async def archive_old_data(
        self,
        table: str,
        dataset: str,
        days_threshold: int = 90,
        archive_dataset: Optional[str] = None,
        market_type: Optional[str] = None,
    ) -> dict:
        """Archive data older than threshold to archive tables.

        Args:
            table: Source table name
            dataset: Source dataset name
            days_threshold: Archive data older than this many days
            archive_dataset: Target archive dataset (defaults to source + "_archive")
            market_type: Optional market type filter (crypto, gold)

        Returns:
            Archival statistics
        """
        if not self.client:
            raise BigQueryError("Client not initialized")

        archive_dataset = archive_dataset or f"{dataset}_archive"
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        try:
            archive_table_ref = f"{self.project_id}.{archive_dataset}.{table}_archive"
            source_table_ref = f"{self.project_id}.{dataset}.{table}"

            # Check if archive table exists
            try:
                self.client.get_table(archive_table_ref)
                logger.debug(f"Archive table exists: {archive_table_ref}")
            except Exception:
                # Create archive table with same schema
                source_table = self.client.get_table(source_table_ref)
                archive_table = bigquery.Table(
                    archive_table_ref,
                    schema=source_table.schema,
                )
                archive_table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.MONTH,
                    field="collected_at" if "collected_at" in [f.name for f in source_table.schema]
                        else "processed_at" if "processed_at" in [f.name for f in source_table.schema]
                        else None,
                )
                self.client.create_table(archive_table)
                logger.info(f"Created archive table: {archive_table_ref}")

            logger.info(
                "Archive operation prepared",
                source=source_table_ref,
                archive=archive_table_ref,
                cutoff=cutoff_date.isoformat(),
                market_type=market_type,
            )

            return {
                "operation": "archive",
                "source_table": source_table_ref,
                "archive_table": archive_table_ref,
                "cutoff_date": cutoff_date.isoformat(),
                "market_type": market_type,
                "status": "prepared",
                "message": "Archive table created, run deletion after verification",
            }

        except Exception as e:
            logger.error("Archive operation failed", error=str(e))
            raise BigQueryError(f"Archive failed: {e}")

    async def delete_old_data(
        self,
        table: str,
        dataset: str,
        days_threshold: int = 180,
        dry_run: bool = True,
        market_type: Optional[str] = None,
    ) -> dict:
        """Delete data older than threshold from tables.

        WARNING: This permanently deletes data. Use with caution.

        Args:
            table: Table name
            dataset: Dataset name
            days_threshold: Delete data older than this many days
            dry_run: If True, only return what would be deleted
            market_type: Optional market type filter

        Returns:
            Deletion statistics
        """
        if not self.client:
            raise BigQueryError("Client not initialized")

        table_ref = f"{self.project_id}.{dataset}.{table}"
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        try:
            # Count what would be deleted
            market_filter = ""
            if market_type:
                market_filter = f"AND market_type = '{market_type}'"
                
            count_query = f"""
            SELECT COUNT(*) as count
            FROM `{table_ref}`
            WHERE collected_at < TIMESTAMP('{cutoff_date.isoformat()}')
            {market_filter}
            """

            count_job = self.client.query(count_query)
            count_result = list(count_job.result())[0]
            rows_to_delete = count_result.count

            if dry_run:
                return {
                    "operation": "delete_preview",
                    "table": table_ref,
                    "cutoff_date": cutoff_date.isoformat(),
                    "rows_to_delete": rows_to_delete,
                    "market_type": market_type,
                    "dry_run": True,
                    "message": f"Would delete {rows_to_delete} rows. Set dry_run=False to execute.",
                }

            # Execute deletion
            delete_query = f"""
            DELETE FROM `{table_ref}`
            WHERE collected_at < TIMESTAMP('{cutoff_date.isoformat()}')
            {market_filter}
            """

            delete_job = self.client.query(delete_query)
            delete_job.result()

            logger.warning(
                "Data deletion executed",
                table=table_ref,
                cutoff=cutoff_date.isoformat(),
                rows_deleted=rows_to_delete,
                market_type=market_type,
            )

            return {
                "operation": "delete",
                "table": table_ref,
                "cutoff_date": cutoff_date.isoformat(),
                "rows_deleted": rows_to_delete,
                "market_type": market_type,
                "dry_run": False,
            }

        except Exception as e:
            logger.error("Deletion failed", error=str(e))
            raise BigQueryError(f"Deletion failed: {e}")

    async def optimize_storage(self, dataset: str) -> dict:
        """Run storage optimization operations."""
        if not self.client:
            raise BigQueryError("Client not initialized")

        results = {
            "dataset": dataset,
            "operations": [],
        }

        try:
            tables = list(self.client.list_tables(f"{self.project_id}.{dataset}"))

            for table in tables:
                table_ref = f"{self.project_id}.{dataset}.{table.table_id}"
                table_info = self.client.get_table(table_ref)

                if table_info.time_partitioning:
                    results["operations"].append({
                        "table": table.table_id,
                        "partitioned": True,
                        "partition_type": table_info.time_partitioning.type_,
                        "num_partitions": table_info.num_partitions or "unknown",
                        "recommendation": "Use partition expiration for automatic cleanup",
                    })
                else:
                    results["operations"].append({
                        "table": table.table_id,
                        "partitioned": False,
                        "recommendation": "Consider partitioning for large tables",
                    })

            return results

        except Exception as e:
            logger.error("Storage optimization failed", error=str(e))
            raise BigQueryError(f"Optimization failed: {e}")

    async def apply_retention_policy(
        self,
        full_auto: bool = False,
        dry_run: bool = True,
        market_type: Optional[str] = None,
    ) -> dict:
        """Apply comprehensive retention policy to all tables in unified dataset.

        Retention Policy (single dataset):
        - raw_data (bronze layer): Archive after 90 days, delete after 180 days
        - sentiment_analysis (silver layer): Archive after 90 days, delete after 365 days
        - Other tables (gold layer): Keep indefinitely or archive based on use case

        Args:
            full_auto: If True, execute all operations automatically
            dry_run: If True, only preview what would be done
            market_type: Optional market type filter

        Returns:
            Policy application results
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "market_type": market_type,
            "dataset": self.dataset,
            "operations": [],
        }

        # raw_data table (bronze layer) - aggressive cleanup
        try:
            raw_archive = await self.archive_old_data(
                "raw_data",
                self.dataset,
                days_threshold=settings.data_retention_bronze_days or 90,
                market_type=market_type,
            )
            results["operations"].append(raw_archive)

            if full_auto and not dry_run:
                raw_delete = await self.delete_old_data(
                    "raw_data",
                    self.dataset,
                    days_threshold=settings.data_retention_bronze_days or 180,
                    dry_run=False,
                    market_type=market_type,
                )
                results["operations"].append(raw_delete)

        except Exception as e:
            logger.error("raw_data retention failed", error=str(e))
            results["operations"].append({
                "table": "raw_data",
                "error": str(e),
            })

        # sentiment_analysis table (silver layer) - moderate cleanup
        try:
            sentiment_archive = await self.archive_old_data(
                "sentiment_analysis",
                self.dataset,
                days_threshold=settings.data_retention_silver_days or 90,
                market_type=market_type,
            )
            results["operations"].append(sentiment_archive)

            if full_auto and not dry_run:
                sentiment_delete = await self.delete_old_data(
                    "sentiment_analysis",
                    self.dataset,
                    days_threshold=settings.data_retention_silver_days or 365,
                    dry_run=False,
                    market_type=market_type,
                )
                results["operations"].append(sentiment_delete)

        except Exception as e:
            logger.error("sentiment_analysis retention failed", error=str(e))
            results["operations"].append({
                "table": "sentiment_analysis",
                "error": str(e),
            })

        # Gold layer tables - optimization only, no deletion
        gold_tables = ["predictions", "prediction_accuracy", "alerts", "analytics_summary", "market_context"]
        for table in gold_tables:
            try:
                table_optimize = await self.optimize_storage(self.dataset)
                # Add table info to results
                results["operations"].append({
                    "table": table,
                    "operation": "optimize",
                    "dataset": self.dataset,
                    "status": "completed",
                    "details": table_optimize,
                })
            except Exception as e:
                logger.error(f"{table} optimization failed", error=str(e))
                results["operations"].append({
                    "table": table,
                    "dataset": self.dataset,
                    "error": str(e),
                })

        return results

    async def close(self) -> None:
        """Close BigQuery client."""
        if self.client:
            self.client.close()
            self.client = None


async def run_retention_job(
    full_auto: bool = False,
    dry_run: bool = True,
    market_type: Optional[str] = None,
) -> dict:
    """Convenience function to run retention policy."""
    manager = DataRetentionManager()
    await manager.initialize()

    try:
        results = await manager.apply_retention_policy(
            full_auto=full_auto,
            dry_run=dry_run,
            market_type=market_type,
        )
        return results
    finally:
        await manager.close()
