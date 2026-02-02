# Pub/Sub Topics for Agent Communication

# Agent command topic
resource "google_pubsub_topic" "agent_commands" {
  name    = "agent-commands-${var.environment}"
  project = var.project_id

  message_retention_duration = "86600s"

  depends_on = [google_project_service.apis]
}

# Agent response topic
resource "google_pubsub_topic" "agent_responses" {
  name    = "agent-responses-${var.environment}"
  project = var.project_id

  message_retention_duration = "86600s"
}

# Risk alerts topic
resource "google_pubsub_topic" "risk_alerts" {
  name    = "risk-alerts-${var.environment}"
  project = var.project_id

  message_retention_duration = "604800s" # 7 days
}

# Price alerts topic
resource "google_pubsub_topic" "price_alerts" {
  name    = "price-alerts-${var.environment}"
  project = var.project_id

  message_retention_duration = "604800s"
}

# Audit logging topic
resource "google_pubsub_topic" "audit_logs" {
  name    = "audit-logs-${var.environment}"
  project = var.project_id

  message_retention_duration = "2592000s" # 30 days
}

# Subscriptions
resource "google_pubsub_subscription" "risk_alerts_push" {
  name  = "risk-alerts-push-${var.environment}"
  topic = google_pubsub_topic.risk_alerts.name

  push_config {
    push_endpoint = "https://agent-gateway-${var.environment}-hash.a.run.app/alerts/risk"

    attributes = {
      x-goog-version = "v1"
    }
  }

  ack_deadline_seconds = 20
}

resource "google_pubsub_subscription" "price_alerts_push" {
  name  = "price-alerts-push-${var.environment}"
  topic = google_pubsub_topic.price_alerts.name

  push_config {
    push_endpoint = "https://agent-gateway-${var.environment}-hash.a.run.app/alerts/price"

    attributes = {
      x-goog-version = "v1"
    }
  }

  ack_deadline_seconds = 20
}

resource "google_pubsub_subscription" "audit_logs_bigquery" {
  name  = "audit-logs-bigquery-${var.environment}"
  topic = google_pubsub_topic.audit_logs.name

  bigquery_config {
    table            = "${var.project_id}.agent_audit_logs.conversations"
    use_topic_schema = false
    write_metadata   = true
  }
}
