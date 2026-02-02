#!/usr/bin/env python3
"""
BigQuery Setup Utility for Sentilyze

This script creates datasets, tables, and loads schemas for the Sentilyze
BigQuery data warehouse.

Usage:
    python bq_setup.py --project <project-id> --environment <env>
    python bq_setup.py --project my-project --environment dev --dry-run
"""

import argparse
import json
import sys
from typing import Dict, List, Optional
from pathlib import Path

try:
    from google.cloud import bigquery
    from google.cloud.exceptions import Conflict, NotFound
except ImportError:
    print("Error: google-cloud-bigquery is required. Install with: pip install google-cloud-bigquery")
    sys.exit(1)


# Default schemas for Sentilyze tables (unified dataset architecture)
# Tables organized by layer: raw_data (bronze), sentiment_analysis/market_context (silver), rest (gold)
TABLE_SCHEMAS = {
    # Bronze layer - raw ingested events
    "raw_data": [
        bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("market_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("payload", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("metadata", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("collected_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("processing_status", "STRING", mode="REQUIRED"),
    ],
    # Silver layer - processed sentiment events
    "sentiment_analysis": [
        bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("market_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("symbols", "STRING", mode="REPEATED"),
        bigquery.SchemaField("sentiment", "RECORD", mode="REQUIRED", fields=[
            bigquery.SchemaField("score", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("label", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("confidence", "FLOAT", mode="REQUIRED"),
        ]),
        bigquery.SchemaField("entities", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("keywords", "STRING", mode="REPEATED"),
        bigquery.SchemaField("content_preview", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("processed_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ],
    # Silver layer - market context data
    "market_context": [
        bigquery.SchemaField("context_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("market_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("price_data", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("volume", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("indicators", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("market_regime", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("anomaly_flags", "STRING", mode="REPEATED"),
        bigquery.SchemaField("correlation_data", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ],
    # Gold layer - predictions
    "predictions": [
        bigquery.SchemaField("prediction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("market_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("prediction_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("predicted_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("horizon_hours", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("target_price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("confidence_score", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("direction", "STRING", mode="REQUIRED"),  # up, down, sideways
        bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("input_features", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("metadata", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ],
    # Gold layer - prediction accuracy tracking
    "prediction_accuracy": [
        bigquery.SchemaField("accuracy_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("prediction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("predicted_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("actual_price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("actual_direction", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("price_difference", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("direction_correct", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("accuracy_score", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("validated_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("tracking_status", "STRING", mode="REQUIRED"),  # pending, validated, expired
    ],
    # Gold layer - alerts
    "alerts": [
        bigquery.SchemaField("alert_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("alert_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("severity", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("symbol", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("market_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("message", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("data", "JSON", mode="NULLABLE"),
        bigquery.SchemaField("triggered_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("sent_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("channels", "STRING", mode="REPEATED"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),  # triggered, sent, failed, acknowledged
    ],
    # Gold layer - analytics summary
    "analytics_summary": [
        bigquery.SchemaField("summary_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("metric", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("value", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("window_start", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("window_end", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("dimensions", "JSON", mode="NULLABLE"),  # symbol, market_type, etc.
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ],
}

# Table time partitioning configuration
TABLE_PARTITIONING = {
    "raw_data": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="collected_at",
        expiration_ms=7776000000,  # 90 days
    ),
    "sentiment_analysis": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="processed_at",
        expiration_ms=31536000000,  # 365 days
    ),
    "market_context": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp",
        expiration_ms=31536000000,  # 365 days
    ),
    "predictions": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="predicted_at",
        expiration_ms=157680000000,  # 5 years
    ),
    "prediction_accuracy": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="validated_at",
        expiration_ms=157680000000,  # 5 years
    ),
    "alerts": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="triggered_at",
        expiration_ms=15552000000,  # 180 days
    ),
    "analytics_summary": bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="created_at",
        expiration_ms=31536000000,  # 365 days
    ),
}

# Table clustering fields
TABLE_CLUSTERING = {
    "raw_data": ["source", "event_type", "market_type"],
    "sentiment_analysis": ["market_type", "source"],
    "market_context": ["symbol", "market_type"],
    "predictions": ["symbol", "market_type", "prediction_type"],
    "prediction_accuracy": ["symbol", "tracking_status"],
    "alerts": ["alert_type", "severity"],
    "analytics_summary": ["metric"],
}


class BigQuerySetup:
    """BigQuery setup and configuration manager."""
    
    def __init__(self, project_id: str, environment: str, dry_run: bool = False):
        self.project_id = project_id
        self.environment = environment
        self.dry_run = dry_run
        self.dataset_id = f"sentilyze_{environment}"
        
        if not dry_run:
            self.client = bigquery.Client(project=project_id)
        else:
            self.client = None
            print(f"[DRY RUN] Would use project: {project_id}")
    
    def create_dataset(self) -> bool:
        """Create the BigQuery dataset if it doesn't exist."""
        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        
        if self.dry_run:
            print(f"[DRY RUN] Would create dataset: {dataset_ref}")
            return True
        
        try:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"  # Adjust based on your needs
            dataset.description = f"Sentilyze data warehouse - {self.environment} environment"
            dataset.labels = {
                "environment": self.environment,
                "project": "sentilyze",
                "managed_by": "bq_setup"
            }
            
            self.client.create_dataset(dataset, exists_ok=True)
            print(f"✓ Dataset created/verified: {dataset_ref}")
            return True
            
        except Exception as e:
            print(f"✗ Error creating dataset: {e}")
            return False
    
    def create_table(self, table_name: str) -> bool:
        """Create a BigQuery table with proper schema and partitioning."""
        table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
        
        if table_name not in TABLE_SCHEMAS:
            print(f"✗ Unknown table: {table_name}")
            return False
        
        if self.dry_run:
            print(f"[DRY RUN] Would create table: {table_id}")
            return True
        
        try:
            schema = TABLE_SCHEMAS[table_name]
            table = bigquery.Table(table_id, schema=schema)
            
            # Add time partitioning if configured
            if TABLE_PARTITIONING.get(table_name):
                table.time_partitioning = TABLE_PARTITIONING[table_name]
                print(f"  - Time partitioning: {table.time_partitioning.type_}")
            
            # Add clustering if configured
            clustering_fields = TABLE_CLUSTERING.get(table_name, [])
            if clustering_fields:
                table.clustering_fields = clustering_fields
                print(f"  - Clustering: {clustering_fields}")
            
            table = self.client.create_table(table, exists_ok=True)
            print(f"✓ Table created/verified: {table_id}")
            return True
            
        except Exception as e:
            print(f"✗ Error creating table {table_name}: {e}")
            return False
    
    def setup_all_tables(self) -> bool:
        """Create all configured tables."""
        print(f"\nSetting up tables for dataset: {self.dataset_id}")
        print("=" * 60)
        
        all_success = True
        for table_name in TABLE_SCHEMAS.keys():
            if not self.create_table(table_name):
                all_success = False
        
        return all_success
    
    def create_views(self) -> bool:
        """Create useful views for data analysis."""
        views = {
            "sentiment_summary": f"""
                SELECT 
                    DATE(timestamp) as analysis_date,
                    sentiment_label,
                    language,
                    COUNT(*) as count,
                    AVG(sentiment_score) as avg_score,
                    AVG(confidence) as avg_confidence
                FROM `{self.project_id}.{self.dataset_id}.sentiment_analysis`
                WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                GROUP BY 1, 2, 3
                ORDER BY 1 DESC, 4 DESC
            """,
            "recent_errors": f"""
                SELECT 
                    timestamp,
                    action,
                    resource_type,
                    resource_id,
                    request_details,
                    ip_address
                FROM `{self.project_id}.{self.dataset_id}.audit_logs`
                WHERE success = FALSE
                    AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
                ORDER BY timestamp DESC
            """,
            "daily_performance": f"""
                SELECT 
                    date,
                    total_analyses,
                    total_texts_processed,
                    avg_processing_time_ms,
                    success_rate,
                    error_count
                FROM `{self.project_id}.{self.dataset_id}.analytics_daily`
                WHERE date > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                ORDER BY date DESC
            """,
        }
        
        print(f"\nCreating views for dataset: {self.dataset_id}")
        print("=" * 60)
        
        all_success = True
        for view_name, query in views.items():
            view_id = f"{self.project_id}.{self.dataset_id}.{view_name}"
            
            if self.dry_run:
                print(f"[DRY RUN] Would create view: {view_id}")
                continue
            
            try:
                view = bigquery.Table(view_id)
                view.view_query = query
                view.view_use_legacy_sql = False
                
                self.client.create_table(view, exists_ok=True)
                print(f"✓ View created/verified: {view_id}")
                
            except Exception as e:
                print(f"✗ Error creating view {view_name}: {e}")
                all_success = False
        
        return all_success
    
    def validate_setup(self) -> bool:
        """Validate that all expected tables and views exist."""
        print(f"\nValidating BigQuery setup for: {self.dataset_id}")
        print("=" * 60)
        
        if self.dry_run:
            print("[DRY RUN] Skipping validation")
            return True
        
        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        
        try:
            # Check dataset exists
            self.client.get_dataset(dataset_ref)
            print(f"✓ Dataset exists: {dataset_ref}")
        except NotFound:
            print(f"✗ Dataset not found: {dataset_ref}")
            return False
        
        # Check tables
        all_valid = True
        for table_name in TABLE_SCHEMAS.keys():
            table_id = f"{dataset_ref}.{table_name}"
            try:
                self.client.get_table(table_id)
                print(f"✓ Table exists: {table_name}")
            except NotFound:
                print(f"✗ Table not found: {table_name}")
                all_valid = False
        
        return all_valid
    
    def export_schema(self, output_file: Optional[str] = None) -> None:
        """Export table schemas to a JSON file."""
        schemas = {}
        for table_name, schema in TABLE_SCHEMAS.items():
            schemas[table_name] = [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description,
                }
                for field in schema
            ]
        
        if output_file is None:
            output_file = f"bq_schemas_{self.environment}.json"
        
        with open(output_file, 'w') as f:
            json.dump(schemas, f, indent=2)
        
        print(f"✓ Schemas exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="BigQuery Setup Utility for Sentilyze",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bq_setup.py --project my-project --environment dev
  python bq_setup.py --project my-project --environment prod --dry-run
  python bq_setup.py --project my-project --environment dev --export-schema
        """
    )
    
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID"
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment (dev/staging/prod)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing"
    )
    parser.add_argument(
        "--export-schema",
        action="store_true",
        help="Export schemas to JSON file and exit"
    )
    parser.add_argument(
        "--skip-views",
        action="store_true",
        help="Skip creating views"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing setup"
    )
    
    args = parser.parse_args()
    
    # Initialize setup
    setup = BigQuerySetup(
        project_id=args.project,
        environment=args.environment,
        dry_run=args.dry_run
    )
    
    # Export schema and exit if requested
    if args.export_schema:
        setup.export_schema()
        return 0
    
    # Validate only mode
    if args.validate_only:
        if setup.validate_setup():
            print("\n✓ All validations passed")
            return 0
        else:
            print("\n✗ Validation failed")
            return 1
    
    # Full setup
    print("=" * 60)
    print("Sentilyze BigQuery Setup")
    print(f"Project: {args.project}")
    print(f"Environment: {args.environment}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)
    
    success = True
    
    # Create dataset
    if not setup.create_dataset():
        success = False
    
    # Create tables
    if not setup.setup_all_tables():
        success = False
    
    # Create views
    if not args.skip_views:
        if not setup.create_views():
            success = False
    
    # Validate
    if not args.dry_run:
        if not setup.validate_setup():
            success = False
    
    # Final status
    print("\n" + "=" * 60)
    if success:
        print("✓ BigQuery setup completed successfully!")
        print("=" * 60)
        return 0
    else:
        print("✗ BigQuery setup completed with errors")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
