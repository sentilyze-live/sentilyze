# BigQuery Module for Sentilyze

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery Dataset ID"
  type        = string
}

variable "dataset_description" {
  description = "Dataset description"
  type        = string
  default     = "Sentilyze unified dataset for crypto and gold market sentiment analysis"
}

variable "dataset_location" {
  description = "Dataset location"
  type        = string
  default     = "US"
}

variable "tables" {
  description = "Map of table names to configurations"
  type = map(object({
    schema = string
    time_partitioning = optional(object({
      type                     = string
      field                    = string
      expiration_ms            = optional(number)
      require_partition_filter = optional(bool, false)
    }), null)
    clustering      = optional(list(string), [])
    expiration_time = optional(string, null)
  }))
  default = {}
}

variable "views" {
  description = "Map of view names to configurations"
  type = map(object({
    query          = string
    use_legacy_sql = optional(bool, false)
  }))
  default = {}
}

# Dataset
resource "google_bigquery_dataset" "dataset" {
  dataset_id    = var.dataset_id
  friendly_name = "Sentilyze Dataset"
  description   = var.dataset_description
  location      = var.dataset_location
  project       = var.project_id

  default_partition_expiration_ms = null
  default_table_expiration_ms     = null

  labels = {
    project = "sentilyze"
  }

  access {
    role          = "OWNER"
    user_by_email = null
    special_group = "projectOwners"
  }

  access {
    role          = "READER"
    user_by_email = null
    special_group = "projectReaders"
  }

  access {
    role          = "WRITER"
    user_by_email = null
    special_group = "projectWriters"
  }
}

# Tables
resource "google_bigquery_table" "tables" {
  for_each = var.tables

  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = each.key
  project    = var.project_id

  schema = each.value.schema

  dynamic "time_partitioning" {
    for_each = each.value.time_partitioning != null ? [each.value.time_partitioning] : []
    content {
      type                     = time_partitioning.value.type
      field                    = time_partitioning.value.field
      expiration_ms            = time_partitioning.value.expiration_ms
      require_partition_filter = time_partitioning.value.require_partition_filter
    }
  }

  clustering = length(each.value.clustering) > 0 ? each.value.clustering : null

  expiration_time = each.value.expiration_time

  deletion_protection = false
}

# Views
resource "google_bigquery_table" "views" {
  for_each = var.views

  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = each.key
  project    = var.project_id

  view {
    query          = each.value.query
    use_legacy_sql = each.value.use_legacy_sql
  }

  deletion_protection = false
}

# Outputs
output "dataset" {
  description = "BigQuery dataset"
  value       = google_bigquery_dataset.dataset
}

output "tables" {
  description = "BigQuery tables"
  value       = google_bigquery_table.tables
}

output "views" {
  description = "BigQuery views"
  value       = google_bigquery_table.views
}
