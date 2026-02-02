# Firestore Database for Agent Memory
resource "google_firestore_database" "agent_memory" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  app_engine_integration_mode = "DISABLED"

  depends_on = [google_project_service.apis]
}

# Firestore Collections and Indexes
resource "google_firestore_index" "conversations" {
  project    = var.project_id
  database   = google_firestore_database.agent_memory.name
  collection = "conversations"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }

  fields {
    field_path = "agent_type"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "watchlist" {
  project    = var.project_id
  database   = google_firestore_database.agent_memory.name
  collection = "watchlist"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "symbol"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "alerts" {
  project    = var.project_id
  database   = google_firestore_database.agent_memory.name
  collection = "price_alerts"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "triggered"
    order      = "ASCENDING"
  }

  fields {
    field_path = "created_at"
    order      = "DESCENDING"
  }
}
