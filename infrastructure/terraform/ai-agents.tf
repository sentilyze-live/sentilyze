# AI Agent Infrastructure for Sentilyze
# These resources support the AI agent squad system

# Additional Service Account for AI Agents
resource "google_service_account" "agent_sa" {
  account_id   = "sentilyze-ai-agents"
  display_name = "Sentilyze AI Agents Service Account"
  description  = "Service account for AI agent orchestration and chat services"
}

# IAM Permissions for AI Agents
resource "google_project_iam_member" "agent_vertex_ai" {
  project = var.gcp_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_firestore" {
  project = var.gcp_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_pubsub_publisher" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_pubsub_subscriber" {
  project = var.gcp_project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_cloudfunctions" {
  project = var.gcp_project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_bigquery" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_bigquery_job" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_secretmanager" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Pub/Sub Topics for Agent Communication
resource "google_pubsub_topic" "agent_commands" {
  name    = "agent-commands-${var.environment}"
  project = var.gcp_project_id

  message_retention_duration = "86600s"

  labels = {
    type = "agent"
    env  = var.environment
  }

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "agent_responses" {
  name    = "agent-responses-${var.environment}"
  project = var.gcp_project_id

  message_retention_duration = "86600s"

  labels = {
    type = "agent"
    env  = var.environment
  }

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "risk_alerts" {
  name    = "risk-alerts-${var.environment}"
  project = var.gcp_project_id

  message_retention_duration = "604800s" # 7 days

  labels = {
    type = "risk"
    env  = var.environment
  }

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "price_alerts" {
  name    = "price-alerts-${var.environment}"
  project = var.gcp_project_id

  message_retention_duration = "604800s"

  labels = {
    type = "price"
    env  = var.environment
  }

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "audit_logs" {
  name    = "audit-logs-${var.environment}"
  project = var.gcp_project_id

  message_retention_duration = "2592000s" # 30 days

  labels = {
    type = "audit"
    env  = var.environment
  }

  depends_on = [google_project_service.apis]
}

# Storage Bucket for Agent Function Source Code
resource "google_storage_bucket" "agent_functions" {
  name     = "${var.gcp_project_id}-agent-functions-${var.environment}"
  location = var.gcp_region

  uniform_bucket_level_access = true

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
    type        = "agent-functions"
  }

  depends_on = [google_project_service.apis]
}

# Storage Bucket for Agent Memory/Artifacts
resource "google_storage_bucket" "agent_memory" {
  name     = "${var.gcp_project_id}-agent-memory-${var.environment}"
  location = var.gcp_region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365 # Keep for 1 year
    }
  }

  labels = {
    environment = var.environment
    project     = "sentilyze"
    type        = "agent-memory"
  }

  depends_on = [google_project_service.apis]
}

# BigQuery Dataset for Agent Audit Logs
resource "google_bigquery_dataset" "agent_audit" {
  dataset_id  = "agent_audit_logs"
  description = "Audit logs for AI agent conversations and activities"
  project     = var.gcp_project_id
  location    = var.gcp_region

  default_table_expiration_ms = 2592000000 # 30 days

  labels = {
    env = var.environment
  }

  access {
    role          = "OWNER"
    user_by_email = google_service_account.agent_sa.email
  }

  access {
    role   = "READER"
    domain = "sentilyze.com"
  }

  depends_on = [google_project_service.apis]
}

# BigQuery Table for Conversation Audit
resource "google_bigquery_table" "conversations" {
  dataset_id = google_bigquery_dataset.agent_audit.dataset_id
  table_id   = "conversations"
  project    = var.gcp_project_id

  time_partitioning {
    type          = "DAY"
    field         = "timestamp"
    expiration_ms = 2592000000 # 30 days
  }

  clustering = ["user_id", "agent_type"]

  schema = <<EOF
[
  {
    "name": "timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "user_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "agent_type",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "session_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "user_message",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "ai_response",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "compliance_check",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "sentiment_queried",
    "type": "STRING",
    "mode": "REPEATED"
  },
  {
    "name": "response_time_ms",
    "type": "INTEGER",
    "mode": "NULLABLE"
  },
  {
    "name": "ip_address",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF

  depends_on = [google_bigquery_dataset.agent_audit]
}

# Cloud Scheduler Jobs for Agent Heartbeats
resource "google_cloud_scheduler_job" "volatility_monitor" {
  name             = "volatility-monitor-${var.environment}"
  description      = "Monitor market volatility every 15 minutes"
  schedule         = "*/15 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "60s"

  http_target {
    http_method = "POST"
    uri         = "https://agent-orchestrator-${var.gcp_project_id}.cloudfunctions.net/monitor-volatility"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      environment = var.environment
      project_id  = var.gcp_project_id
    }))

    oauth_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "price_check" {
  name             = "price-check-${var.environment}"
  description      = "Check price alerts every 5 minutes"
  schedule         = "*/5 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "60s"

  http_target {
    http_method = "POST"
    uri         = "https://agent-orchestrator-${var.gcp_project_id}.cloudfunctions.net/check-price-alerts"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      environment = var.environment
      project_id  = var.gcp_project_id
    }))

    oauth_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }

  depends_on = [google_project_service.apis]
}

# Secret for Agent System Prompts
resource "google_secret_manager_secret" "agent_system_prompts" {
  secret_id = "AGENT_SYSTEM_PROMPTS"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Secret for Vertex AI Configuration
resource "google_secret_manager_secret" "vertex_ai_config" {
  secret_id = "VERTEX_AI_CONFIG"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
