# Cloud Run Service - Agent Gateway (FastAPI) - COST OPTIMIZED

resource "google_cloud_run_service" "agent_gateway" {
  name     = "agent-gateway-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    metadata {
      annotations = {
        # COST OPTIMIZATION: Scale to 0 when idle (cold start acceptable)
        "autoscaling.knative.dev/minScale" = "0"
        # Limit max instances to control costs
        "autoscaling.knative.dev/maxScale"         = "10"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }

    spec {
      service_account_name = google_service_account.agent_sa.email

      # COST OPTIMIZATION: Reduced resources
      container_concurrency = 100
      timeout_seconds       = 300

      containers {
        image = "gcr.io/${var.project_id}/agent-gateway:${var.environment}"

        resources {
          limits = {
            cpu    = "0.5"   # Reduced from 1
            memory = "256Mi" # Reduced from 512Mi
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "REGION"
          value = var.region
        }

        env {
          name  = "ENABLE_BIGQUERY_CACHE"
          value = "true"
        }

        env {
          name  = "ENABLE_SMART_TRIGGERS"
          value = "true"
        }

        env {
          name  = "ENABLE_VERTEX_AI_FOR_AGENTS"
          value = "true"
        }

        env {
          name  = "VERTEX_AI_LOCATION"
          value = "us-central1"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.apis]
}

# Cloud Run IAM (public access)
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.agent_gateway.name
  location = google_cloud_run_service.agent_gateway.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function - Agent Orchestrator - COST OPTIMIZED
resource "google_cloudfunctions_function" "agent_orchestrator" {
  name        = "agent-orchestrator-${var.environment}"
  description = "Orchestrates AI agent conversations - Cost Optimized"
  runtime     = "python311"

  # COST OPTIMIZATION: Reduced memory from 512MB to 256MB
  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.agent_orchestrator_source.name
  trigger_http          = true
  entry_point           = "handle_request"

  service_account_email = google_service_account.agent_sa.email

  environment_variables = {
    ENVIRONMENT           = var.environment
    PROJECT_ID            = var.project_id
    REGION                = var.region
    VERTEX_AI_LOCATION    = "us-central1"
    PUBSUB_COMMAND_TOPIC  = google_pubsub_topic.agent_commands.name
    PUBSUB_RESPONSE_TOPIC = google_pubsub_topic.agent_responses.name
    # COST OPTIMIZATION FLAGS
    ENABLE_BIGQUERY_CACHE       = "true"
    ENABLE_SMART_TRIGGERS       = "true"
    ENABLE_VERTEX_AI_FOR_AGENTS = "true"
    CACHE_TTL_MINUTES           = "60"
  }

  # COST OPTIMIZATION: Reduced max instances from 50 to 20
  timeout       = 60
  max_instances = 20

  depends_on = [google_project_service.apis]
}

# Cloud Function IAM
resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = google_cloudfunctions_function.agent_orchestrator.project
  region         = google_cloudfunctions_function.agent_orchestrator.region
  cloud_function = google_cloudfunctions_function.agent_orchestrator.name

  role   = "roles/cloudfunctions.invoker"
  member = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Storage Bucket for Function Source Code
resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-agent-functions-${var.environment}"
  location = var.region

  uniform_bucket_level_access = true
}
