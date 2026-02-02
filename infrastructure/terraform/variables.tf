# Sentilyze - Terraform Variables

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# Feature Flags
variable "enable_crypto_market" {
  description = "Enable cryptocurrency market analysis"
  type        = bool
  default     = true
}

variable "enable_gold_market" {
  description = "Enable gold/precious metals market analysis"
  type        = bool
  default     = true
}

variable "enable_crypto_predictions" {
  description = "Enable prediction generation for crypto markets"
  type        = bool
  default     = true
}

variable "enable_gold_predictions" {
  description = "Enable prediction generation for gold markets"
  type        = bool
  default     = true
}

variable "enable_email_alerts" {
  description = "Enable email alert notifications"
  type        = bool
  default     = true
}

variable "enable_slack_alerts" {
  description = "Enable Slack alert notifications"
  type        = bool
  default     = true
}

variable "enable_discord_alerts" {
  description = "Enable Discord alert notifications"
  type        = bool
  default     = false
}

variable "enable_firestore" {
  description = "Enable Firestore database for caching"
  type        = bool
  default     = true
}

variable "enable_postgres" {
  description = "Enable PostgreSQL database"
  type        = bool
  default     = true
}

# Database Configuration
variable "db_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "sentilyze"
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

# GitHub Configuration
variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "sentilyze"
}

# Alert Configuration
variable "alert_email_addresses" {
  description = "List of email addresses for alerts"
  type        = list(string)
  default     = []
}

# Service Scaling
variable "min_instances" {
  description = "Minimum number of instances per service"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances per service"
  type        = number
  default     = 10
}

# Firestore Configuration
variable "firestore_location" {
  description = "Firestore database location"
  type        = string
  default     = "us-central"
}
