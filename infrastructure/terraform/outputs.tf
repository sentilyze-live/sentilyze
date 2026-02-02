# Sentilyze - Terraform Outputs

output "gcp_project_id" {
  description = "GCP Project ID"
  value       = var.gcp_project_id
}

output "gcp_region" {
  description = "GCP Region"
  value       = var.gcp_region
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "firestore_database" {
  description = "Firestore database name"
  value       = var.enable_firestore ? google_firestore_database.database[0].name : null
}

output "firestore_location" {
  description = "Firestore database location"
  value       = var.enable_firestore ? google_firestore_database.database[0].location_id : null
}

output "postgres_host" {
  description = "PostgreSQL instance host"
  value       = var.enable_postgres ? google_sql_database_instance.main[0].private_ip_address : null
  sensitive   = true
}

output "postgres_connection_name" {
  description = "PostgreSQL Cloud SQL connection name"
  value       = var.enable_postgres ? google_sql_database_instance.main[0].connection_name : null
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = "sentilyze_dataset"
}

output "storage_bucket" {
  description = "Main Cloud Storage bucket"
  value       = google_storage_bucket.sentilyze.name
}

output "models_bucket" {
  description = "ML Models Cloud Storage bucket"
  value       = google_storage_bucket.models.name
}

output "service_accounts" {
  description = "Service account emails for each service"
  value = {
    for name, sa in google_service_account.services : name => sa.email
  }
}

output "cloud_run_services" {
  description = "Cloud Run service URLs"
  value = {
    for name, service in google_cloud_run_v2_service.services : name => service.uri
  }
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = google_cloud_run_v2_service.services["api-gateway"].uri
}

output "pubsub_topics" {
  description = "Created Pub/Sub topics"
  value = {
    for name, topic in module.pubsub.topics : name => topic.id
  }
}

output "bigquery_tables" {
  description = "Created BigQuery tables"
  value = {
    for name, table in module.bigquery.tables : name => table.id
  }
}

output "enabled_markets" {
  description = "Markets enabled in this deployment"
  value = {
    crypto = var.enable_crypto_market
    gold   = var.enable_gold_market
  }
}

output "enabled_predictions" {
  description = "Prediction types enabled in this deployment"
  value = {
    crypto = var.enable_crypto_predictions
    gold   = var.enable_gold_predictions
  }
}
