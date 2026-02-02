# Pub/Sub Module for Sentilyze

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "topics" {
  description = "Map of topic names to configurations"
  type = map(object({
    message_retention_duration = optional(string, "86600s")
    labels                     = optional(map(string), {})
    kms_key_name               = optional(string, null)
  }))
  default = {}
}

variable "push_subscriptions" {
  description = "Map of push subscription names to configurations"
  type = map(object({
    topic_name                 = string
    push_endpoint              = string
    ack_deadline_seconds       = optional(number, 60)
    message_retention_duration = optional(string, "86400s")
    service_account_email      = optional(string, null)
    attributes                 = optional(map(string), {})
    dead_letter_policy = optional(object({
      dead_letter_topic     = string
      max_delivery_attempts = number
    }), null)
    retry_policy = optional(object({
      minimum_backoff = string
      maximum_backoff = string
    }), null)
  }))
  default = {}
}

variable "pull_subscriptions" {
  description = "Map of pull subscription names to configurations"
  type = map(object({
    topic_name                 = string
    ack_deadline_seconds       = optional(number, 60)
    message_retention_duration = optional(string, "86400s")
    retain_acked_messages      = optional(bool, false)
    expiration_policy_ttl      = optional(string, "")
    dead_letter_policy = optional(object({
      dead_letter_topic     = string
      max_delivery_attempts = number
    }), null)
  }))
  default = {}
}

# Topics
resource "google_pubsub_topic" "topics" {
  for_each = var.topics

  name    = each.key
  project = var.project_id

  message_retention_duration = each.value.message_retention_duration
  labels                     = each.value.labels

  dynamic "message_storage_policy" {
    for_each = each.value.kms_key_name != null ? [1] : []
    content {
      allowed_persistence_regions = []
    }
  }

  dynamic "schema_settings" {
    for_each = each.value.kms_key_name != null ? [1] : []
    content {
      schema   = each.value.kms_key_name
      encoding = "JSON"
    }
  }
}

# Push Subscriptions
resource "google_pubsub_subscription" "push" {
  for_each = var.push_subscriptions

  name  = each.key
  topic = google_pubsub_topic.topics[each.value.topic_name].id

  ack_deadline_seconds       = each.value.ack_deadline_seconds
  message_retention_duration = each.value.message_retention_duration
  retain_acked_messages      = false
  enable_message_ordering    = false

  push_config {
    push_endpoint = each.value.push_endpoint

    attributes = each.value.attributes

    dynamic "oidc_token" {
      for_each = each.value.service_account_email != null ? [1] : []
      content {
        service_account_email = each.value.service_account_email
        audience              = each.value.push_endpoint
      }
    }
  }

  dynamic "dead_letter_policy" {
    for_each = each.value.dead_letter_policy != null ? [1] : []
    content {
      dead_letter_topic     = each.value.dead_letter_policy.dead_letter_topic
      max_delivery_attempts = each.value.dead_letter_policy.max_delivery_attempts
    }
  }

  dynamic "retry_policy" {
    for_each = each.value.retry_policy != null ? [1] : []
    content {
      minimum_backoff = each.value.retry_policy.minimum_backoff
      maximum_backoff = each.value.retry_policy.maximum_backoff
    }
  }
}

# Pull Subscriptions
resource "google_pubsub_subscription" "pull" {
  for_each = var.pull_subscriptions

  name  = each.key
  topic = google_pubsub_topic.topics[each.value.topic_name].id

  ack_deadline_seconds       = each.value.ack_deadline_seconds
  message_retention_duration = each.value.message_retention_duration
  retain_acked_messages      = each.value.retain_acked_messages
  enable_message_ordering    = false

  dynamic "expiration_policy" {
    for_each = each.value.expiration_policy_ttl != "" ? [1] : []
    content {
      ttl = each.value.expiration_policy_ttl
    }
  }

  dynamic "dead_letter_policy" {
    for_each = each.value.dead_letter_policy != null ? [1] : []
    content {
      dead_letter_topic     = each.value.dead_letter_policy.dead_letter_topic
      max_delivery_attempts = each.value.dead_letter_policy.max_delivery_attempts
    }
  }
}

# Outputs
output "topics" {
  description = "Created Pub/Sub topics"
  value       = google_pubsub_topic.topics
}

output "push_subscriptions" {
  description = "Created push subscriptions"
  value       = google_pubsub_subscription.push
}

output "pull_subscriptions" {
  description = "Created pull subscriptions"
  value       = google_pubsub_subscription.pull
}
