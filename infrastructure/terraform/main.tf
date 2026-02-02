# Sentilyze - Main Terraform Configuration
# Unified infrastructure for Crypto and Gold market sentiment analysis

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "gcs" {
    bucket = "sentilyze-v5-clean-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "pubsub.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "firestore.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudfunctions.googleapis.com",
    "eventarc.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
  ])

  project = var.gcp_project_id
  service = each.value

  disable_dependent_services = false
  disable_on_destroy         = false
}

# Service Accounts
resource "google_service_account" "services" {
  for_each = toset([
    "api-gateway",
    "ingestion",
    "sentiment-processor",
    "market-context-processor",
    "prediction-engine",
    "alert-service",
    "tracker-service",
    "analytics-engine",
  ])

  account_id   = "sentilyze-${each.value}"
  display_name = "Sentilyze ${each.value} Service Account"
  description  = "Service account for ${each.value} service"
}

# IAM Bindings for Service Accounts
resource "google_project_iam_member" "ingestion_pubsub" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.services["ingestion"].email}"
}

resource "google_project_iam_member" "sentiment_processor_pubsub" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.services["sentiment-processor"].email}"
}

resource "google_project_iam_member" "sentiment_processor_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.services["sentiment-processor"].email}"
}

resource "google_project_iam_member" "sentiment_processor_vertex" {
  project = var.gcp_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.services["sentiment-processor"].email}"
}

resource "google_project_iam_member" "market_context_pubsub" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.services["market-context-processor"].email}"
}

resource "google_project_iam_member" "market_context_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.services["market-context-processor"].email}"
}

resource "google_project_iam_member" "prediction_engine_pubsub" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.services["prediction-engine"].email}"
}

resource "google_project_iam_member" "prediction_engine_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.services["prediction-engine"].email}"
}

resource "google_project_iam_member" "prediction_engine_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.services["prediction-engine"].email}"
}

resource "google_project_iam_member" "alert_service_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.services["alert-service"].email}"
}

resource "google_project_iam_member" "tracker_service_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.services["tracker-service"].email}"
}

resource "google_project_iam_member" "analytics_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.services["analytics-engine"].email}"
}

resource "google_project_iam_member" "analytics_bigquery_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.services["analytics-engine"].email}"
}

resource "google_project_iam_member" "all_services_secretmanager" {
  for_each = google_service_account.services
  project  = var.gcp_project_id
  role     = "roles/secretmanager.secretAccessor"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "all_services_pubsub_subscriber" {
  for_each = google_service_account.services
  project  = var.gcp_project_id
  role     = "roles/pubsub.subscriber"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "all_services_firestore" {
  for_each = google_service_account.services
  project  = var.gcp_project_id
  role     = "roles/datastore.user"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "all_services_logging" {
  for_each = google_service_account.services
  project  = var.gcp_project_id
  role     = "roles/logging.logWriter"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "all_services_monitoring" {
  for_each = google_service_account.services
  project  = var.gcp_project_id
  role     = "roles/monitoring.metricWriter"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "all_services_cloudtrace" {
  for_each = google_service_account.services
  project  = var.gcp_project_id
  role     = "roles/cloudtrace.agent"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "cloud_run_invoker_all_users" {
  for_each = local.services
  project  = var.gcp_project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Storage Bucket for data and models
resource "google_storage_bucket" "sentilyze" {
  name          = "${var.gcp_project_id}-sentilyze"
  location      = var.gcp_region
  force_destroy = var.environment != "production"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }

  labels = {
    environment = var.environment
    project     = "sentilyze"
  }
}

# Cloud Storage for ML Models
resource "google_storage_bucket" "models" {
  name          = "${var.gcp_project_id}-sentilyze-models"
  location      = var.gcp_region
  force_destroy = false

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    project     = "sentilyze"
    type        = "models"
  }
}

# Firestore for caching and session storage (Google-native alternative to Redis)
resource "google_app_engine_application" "app" {
  count       = var.enable_firestore ? 1 : 0
  project     = var.gcp_project_id
  location_id = var.gcp_region

  depends_on = [google_project_service.apis]
}

resource "google_firestore_database" "database" {
  count       = var.enable_firestore ? 1 : 0
  project     = var.gcp_project_id
  name        = "(default)"
  location_id = var.gcp_region
  type        = "FIRESTORE_NATIVE"

  app_engine_integration_mode = "ENABLED"

  depends_on = [google_app_engine_application.app]
}

# Cloud SQL for PostgreSQL (Prediction Tracking)
resource "google_sql_database_instance" "main" {
  count            = var.enable_postgres ? 1 : 0
  name             = "${var.gcp_project_id}-postgres"
  database_version = "POSTGRES_15"
  region           = var.gcp_region

  settings {
    tier = var.environment == "production" ? "db-n1-standard-2" : "db-f1-micro"

    backup_configuration {
      enabled    = var.environment == "production"
      start_time = "03:00"
    }

    ip_configuration {
      ipv4_enabled = true
      # No authorized_networks - database is only accessible via Private IP or Cloud SQL Proxy
      # Access restricted to VPC and Cloud Run services via service accounts
    }
  }

  deletion_protection = var.environment == "production"

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "predictions" {
  count    = var.enable_postgres ? 1 : 0
  name     = "sentilyze_predictions"
  instance = google_sql_database_instance.main[0].name
}

resource "google_sql_user" "postgres" {
  count    = var.enable_postgres ? 1 : 0
  name     = var.db_user
  instance = google_sql_database_instance.main[0].name
  password = var.db_password
}

# Pub/Sub Module
module "pubsub" {
  source = "./modules/pubsub"

  project_id = var.gcp_project_id

  topics = {
    "raw-events" = {
      message_retention_duration = "86600s"
      labels = {
        type = "raw"
      }
    }
    "processed-events" = {
      message_retention_duration = "86600s"
      labels = {
        type = "processed"
      }
    }
    "market-context" = {
      message_retention_duration = "86600s"
      labels = {
        type = "context"
      }
    }
    "processed-sentiment" = {
      message_retention_duration = "86600s"
      labels = {
        type = "intermediate"
      }
    }
    "predictions" = {
      message_retention_duration = "604800s" # 7 days
      labels = {
        type = "predictions"
      }
    }
    "alerts" = {
      message_retention_duration = "604800s"
      labels = {
        type = "alerts"
      }
    }
    "analytics-events" = {
      message_retention_duration = "2592000s" # 30 days
      labels = {
        type = "analytics"
      }
    }
  }

  # Pub/Sub Push Subscriptions - Cloud Run compatible (scale-to-zero)
  push_subscriptions = {
    # Sentiment Processor - raw events → processed sentiment
    "raw-data-subscription" = {
      topic_name           = "raw-events"
      push_endpoint        = "https://sentiment-processor-${var.gcp_project_id}.run.app/pubsub-push/raw-events"
      ack_deadline_seconds = 60
      service_account_email = google_service_account.services["sentiment-processor"].email
    }
    
    # Market Context Processor - processed sentiment → market context
    "processed-sentiment-subscription" = {
      topic_name           = "processed-sentiment"
      push_endpoint        = "https://market-context-processor-${var.gcp_project_id}.run.app/pubsub-push/processed-sentiment"
      ack_deadline_seconds = 60
      service_account_email = google_service_account.services["market-context-processor"].email
    }
    
    # Prediction Engine - market context → predictions
    "market-context-subscription" = {
      topic_name           = "market-context"
      push_endpoint        = "https://prediction-engine-${var.gcp_project_id}.run.app/pubsub-push/market-context"
      ack_deadline_seconds = 60
      service_account_email = google_service_account.services["prediction-engine"].email
    }
    
    # Alert Service - predictions → alerts
    "predictions-subscription-alerts" = {
      topic_name           = "predictions"
      push_endpoint        = "https://alert-service-${var.gcp_project_id}.run.app/pubsub-push/alerts"
      ack_deadline_seconds = 60
      service_account_email = google_service_account.services["alert-service"].email
    }
    
    # Tracker Service - predictions → outcome tracking
    "predictions-subscription-tracker" = {
      topic_name           = "predictions"
      push_endpoint        = "https://tracker-service-${var.gcp_project_id}.run.app/pubsub-push/predictions"
      ack_deadline_seconds = 60
      service_account_email = google_service_account.services["tracker-service"].email
    }
  }

  # Pull Subscriptions - Analytics (can use pull for batch processing)
  pull_subscriptions = {
    "analytics-events-subscription" = {
      topic_name                 = "analytics-events"
      ack_deadline_seconds       = 120
      message_retention_duration = "86400s"
    }
  }

    # Alert Service - predictions → alerts
    "predictions-subscription-alerts" = {
      topic_name            = "predictions"
      push_endpoint         = "https://alert-service-${var.gcp_project_id}.run.app/pubsub-push/alerts"
      ack_deadline_seconds  = 60
      service_account_email = google_service_account.services["alert-service"].email
    }
  }

  # Pull Subscriptions - require persistent connections (not Cloud Run scale-to-zero compatible)
  # TODO: Convert these to push subscriptions after adding pubsub endpoints to services
  pull_subscriptions = {
    "analytics-events-subscription" = {
      topic_name                 = "analytics-events"
      ack_deadline_seconds       = 120
      message_retention_duration = "86400s"
    }
    # Placeholder subscriptions for event chain (services need pubsub endpoint implementation)
    "processed-sentiment-subscription-pull" = {
      topic_name           = "processed-sentiment"
      ack_deadline_seconds = 60
    }
    "market-context-subscription-pull" = {
      topic_name           = "market-context"
      ack_deadline_seconds = 60
    }
    "predictions-subscription-tracker-pull" = {
      topic_name           = "predictions"
      ack_deadline_seconds = 60
    }
  }

  depends_on = [google_project_service.apis]
}

# BigQuery Module
module "bigquery" {
  source = "./modules/bigquery"

  project_id = var.gcp_project_id
  region     = var.gcp_region
  dataset_id = "sentilyze_dataset"

  tables = {
    "raw_data" = {
      schema = file("${path.module}/schemas/raw_data.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "timestamp"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type", "data_source"]
    }
    "sentiment_analysis" = {
      schema = file("${path.module}/schemas/sentiment_analysis.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "timestamp"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type", "sentiment_label"]
    }
    "market_context" = {
      schema = file("${path.module}/schemas/market_context.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "timestamp"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type", "asset_symbol"]
    }
    "predictions" = {
      schema = file("${path.module}/schemas/predictions.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "prediction_timestamp"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type", "asset_symbol", "prediction_type"]
    }
    "prediction_accuracy" = {
      schema = file("${path.module}/schemas/prediction_accuracy.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "validation_timestamp"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type", "asset_symbol"]
    }
    "alerts" = {
      schema = file("${path.module}/schemas/alerts.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "created_at"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type", "alert_type", "severity"]
    }
    "analytics_summary" = {
      schema = file("${path.module}/schemas/analytics_summary.json")
      time_partitioning = {
        type                     = "DAY"
        field                    = "date"
        expiration_ms            = null
        require_partition_filter = false
      }
      clustering = ["market_type"]
    }
  }

  views = {
    "daily_sentiment_summary" = {
      query = templatefile("${path.module}/views/daily_sentiment_summary.sql", {
        project_id = var.gcp_project_id
        dataset_id = "sentilyze_dataset"
      })
      use_legacy_sql = false
    }
    "prediction_performance" = {
      query = templatefile("${path.module}/views/prediction_performance.sql", {
        project_id = var.gcp_project_id
        dataset_id = "sentilyze_dataset"
      })
      use_legacy_sql = false
    }
    "crypto_market_overview" = {
      query = templatefile("${path.module}/views/crypto_market_overview.sql", {
        project_id = var.gcp_project_id
        dataset_id = "sentilyze_dataset"
      })
      use_legacy_sql = false
    }
    "gold_market_overview" = {
      query = templatefile("${path.module}/views/gold_market_overview.sql", {
        project_id = var.gcp_project_id
        dataset_id = "sentilyze_dataset"
      })
      use_legacy_sql = false
    }
  }

  depends_on = [google_project_service.apis]
}

# Secret Manager for sensitive configuration
# Secret IDs must match what the code expects (see shared/sentilyze_core/config/gcp.py)
resource "google_secret_manager_secret" "secrets" {
  for_each = toset([
    "db-password",
    # Crypto API keys
    "COINGECKO_API_KEY",
    "FINNHUB_API_KEY",
    "EODHD_API_KEY",
    "BINANCE_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "CRYPTOPANIC_API_KEY",
    # Gold/Metals API keys
    "GOLDAPI_API_KEY",
    "METALS_API_KEY",
    "TWELVE_DATA_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    # Alerting
    "TELEGRAM_BOT_TOKEN",
    "SLACK_WEBHOOK_URL",
    "DISCORD_WEBHOOK_URL",
    "SMTP_PASSWORD",
    "EMAIL_PASSWORD",
    # ML/AI (optional)
    "OPENAI_API_KEY",
    "HUGGINGFACE_API_KEY",
  ])

  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Cloud Run Services
locals {
  services = {
    "api-gateway" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/api-gateway:latest"
      port  = 8080
      env_vars = {
        "CACHE_TYPE"           = "firestore"
        "BIGQUERY_DATASET"     = "sentilyze_dataset"
        "PUBSUB_PROJECT_ID"    = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT" = var.gcp_project_id
        "ENABLE_CRYPTO_MARKET" = var.enable_crypto_market
        "ENABLE_GOLD_MARKET"   = var.enable_gold_market
      }
      service_account = google_service_account.services["api-gateway"].email
    }
    "ingestion" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/ingestion:latest"
      port  = 8081
      env_vars = {
        "CACHE_TYPE"            = "firestore"
        "PUBSUB_TOPIC_RAW_DATA" = "raw-events"
        "PUBSUB_PROJECT_ID"     = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT"  = var.gcp_project_id
        "ENABLE_CRYPTO_MARKET"  = var.enable_crypto_market
        "ENABLE_GOLD_MARKET"    = var.enable_gold_market
      }
      service_account = google_service_account.services["ingestion"].email
    }
    "sentiment-processor" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/sentiment-processor:latest"
      port  = 8082
      env_vars = {
        "CACHE_TYPE"                       = "firestore"
        "PUBSUB_SUBSCRIPTION_RAW_DATA"     = "raw-data-subscription"
        "PUBSUB_TOPIC_PROCESSED_SENTIMENT" = "processed-sentiment"
        "PUBSUB_TOPIC_PROCESSED_EVENTS"    = "processed-events"
        "PUBSUB_PROJECT_ID"                = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT"             = var.gcp_project_id
        "VERTEX_AI_PROJECT_ID"             = var.gcp_project_id
      }
      service_account = google_service_account.services["sentiment-processor"].email
    }
    "market-context-processor" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/market-context-processor:latest"
      port  = 8083
      env_vars = {
        "CACHE_TYPE"                              = "firestore"
        "BIGQUERY_DATASET"                        = "sentilyze_dataset"
        "PUBSUB_SUBSCRIPTION_PROCESSED_SENTIMENT" = "processed-sentiment-subscription"
        "PUBSUB_TOPIC_MARKET_CONTEXT"             = "market-context"
        "PUBSUB_PROJECT_ID"                       = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT"                    = var.gcp_project_id
      }
      service_account = google_service_account.services["market-context-processor"].email
    }
    "prediction-engine" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/prediction-engine:latest"
      port  = 8084
      env_vars = {
        "CACHE_TYPE"                         = "firestore"
        "BIGQUERY_DATASET"                   = "sentilyze_dataset"
        "DB_HOST"                            = var.enable_postgres ? google_sql_database_instance.main[0].private_ip_address : ""
        "DB_PORT"                            = "5432"
        "DB_NAME"                            = "sentilyze_predictions"
        "PUBSUB_SUBSCRIPTION_MARKET_CONTEXT" = "market-context-subscription"
        "PUBSUB_TOPIC_PREDICTIONS"           = "predictions"
        "PUBSUB_PROJECT_ID"                  = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT"               = var.gcp_project_id
        "ML_MODEL_PATH"                      = "gs://${var.gcp_project_id}-sentilyze-models"
        "ENABLE_CRYPTO_PREDICTIONS"          = var.enable_crypto_predictions
        "ENABLE_GOLD_PREDICTIONS"            = var.enable_gold_predictions
      }
      service_account = google_service_account.services["prediction-engine"].email
    }
    "alert-service" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/alert-service:latest"
      port  = 8085
      env_vars = {
        "CACHE_TYPE"                      = "firestore"
        "PUBSUB_SUBSCRIPTION_PREDICTIONS" = "predictions-subscription-alerts"
        "PUBSUB_PROJECT_ID"               = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT"            = var.gcp_project_id
        "ENABLE_EMAIL_ALERTS"             = var.enable_email_alerts
        "ENABLE_SLACK_ALERTS"             = var.enable_slack_alerts
        "ENABLE_DISCORD_ALERTS"           = var.enable_discord_alerts
      }
      service_account = google_service_account.services["alert-service"].email
    }
    "tracker-service" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/tracker-service:latest"
      port  = 8087
      env_vars = {
        "CACHE_TYPE"                      = "firestore"
        "BIGQUERY_DATASET"                = "sentilyze_dataset"
        "DB_HOST"                         = var.enable_postgres ? google_sql_database_instance.main[0].private_ip_address : ""
        "DB_PORT"                         = "5432"
        "DB_NAME"                         = "sentilyze_predictions"
        "PUBSUB_SUBSCRIPTION_PREDICTIONS" = "predictions-subscription-tracker"
        "PUBSUB_PROJECT_ID"               = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT"            = var.gcp_project_id
      }
      service_account = google_service_account.services["tracker-service"].email
    }
    "analytics-engine" = {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/analytics-engine:latest"
      port  = 8086
      env_vars = {
        "CACHE_TYPE"           = "firestore"
        "BIGQUERY_DATASET"     = "sentilyze_dataset"
        "DB_HOST"              = var.enable_postgres ? google_sql_database_instance.main[0].private_ip_address : ""
        "DB_PORT"              = "5432"
        "DB_NAME"              = "sentilyze_predictions"
        "PUBSUB_PROJECT_ID"    = var.gcp_project_id
        "GOOGLE_CLOUD_PROJECT" = var.gcp_project_id
        "ANALYTICS_CACHE_TTL"  = "300"
      }
      service_account = google_service_account.services["analytics-engine"].email
    }
  }
}

resource "google_cloud_run_v2_service" "services" {
  for_each = local.services

  name     = each.key
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = each.value.service_account

    scaling {
      min_instances = var.environment == "production" ? 1 : 0
      max_instances = var.environment == "production" ? 100 : 10
    }

    containers {
      image = each.value.image

      ports {
        container_port = each.value.port
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "SERVICE_NAME"
        value = each.key
      }
      env {
        name  = "PORT"
        value = tostring(each.value.port)
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.gcp_region
      }

      dynamic "env" {
        for_each = each.value.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = var.environment != "production"
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [google_project_service.apis]
}

# Cloud Build Triggers
resource "google_cloudbuild_trigger" "services" {
  for_each = local.services

  name        = "${each.key}-trigger"
  description = "Trigger for ${each.key} service"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = var.environment == "production" ? "^main$" : "^develop$"
    }
  }

  included_files = ["services/${each.key}/**"]

  build {
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "build",
        "-t", "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:$COMMIT_SHA",
        "-t", "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:latest",
        "-f", "services/${each.key}/Dockerfile",
        "services/${each.key}"
      ]
    }

    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push",
        "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:$COMMIT_SHA"
      ]
    }

    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push",
        "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:latest"
      ]
    }

    step {
      name = "gcr.io/google.com/cloudsdktool/cloud-sdk"
      args = [
        "gcloud", "run", "deploy", each.key,
        "--image", "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:$COMMIT_SHA",
        "--region", var.gcp_region,
        "--platform", "managed",
        "--no-traffic"
      ]
    }

    images = [
      "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:$COMMIT_SHA",
      "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/sentilyze/${each.key}:latest"
    ]
  }

  depends_on = [google_project_service.apis]
}

# Cloud Scheduler for ingestion triggers
resource "google_cloud_scheduler_job" "crypto_ingestion" {
  count = var.enable_crypto_market ? 1 : 0

  name             = "crypto-data-ingestion"
  description      = "Trigger crypto data ingestion every 5 minutes"
  schedule         = "*/5 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.services["ingestion"].uri}/trigger/crypto"

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.services["ingestion"].email
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "gold_ingestion" {
  count = var.enable_gold_market ? 1 : 0

  name             = "gold-data-ingestion"
  description      = "Trigger gold data ingestion every 15 minutes"
  schedule         = "*/15 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.services["ingestion"].uri}/trigger/gold"

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.services["ingestion"].email
    }
  }

  depends_on = [google_project_service.apis]
}

# Monitoring
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate - ${var.environment}"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/log_entry_count\" AND metric.labels.severity=\"ERROR\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].id

  alert_strategy {
    auto_close = "86400s"
  }

  severity = "ERROR"
}

resource "google_monitoring_notification_channel" "email" {
  count = length(var.alert_email_addresses)

  display_name = "Email Notification - ${var.alert_email_addresses[count.index]}"
  type         = "email"

  labels = {
    email_address = var.alert_email_addresses[count.index]
  }
}
