#!/bin/bash
###############################################################################
# Script: manage-secrets.sh
# Description: Secret management utility for Sentilyze
# Usage: ./manage-secrets.sh <command> [options]
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Uses GCP_PROJECT_ID env var or falls back to gcloud configured project
# For project 'sentilyze-v5-clean', ensure gcloud is configured: gcloud config set project sentilyze-v5-clean
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

###############################################################################
# Show Help
###############################################################################
show_help() {
    cat << EOF
Sentilyze Secret Manager Utility

Usage: $0 <command> [options]

Commands:
  list                          List all secrets
  create <name> [value]         Create a new secret (value from arg or prompt)
  update <name> [value]         Update an existing secret
  get <name>                    Get the latest version of a secret
  versions <name>               List all versions of a secret
  rotate <name>                 Rotate a secret (creates new version)
  delete <name>                 Delete a secret
  cleanup <name> [keep-count]   Clean up old versions (default: keep 5)
  import <file>                 Import secrets from JSON file
  export [file]                 Export secrets to JSON file

Options:
  --project <project-id>        GCP project ID
  --env <environment>           Environment (dev/staging/prod)
  --help                        Show this help message

Examples:
  $0 list
  $0 create database-url
  $0 update api-key "new-secret-value"
  $0 rotate jwt-secret
  $0 export secrets-backup.json

EOF
}

###############################################################################
# List Secrets
###############################################################################
list_secrets() {
    log_info "Listing secrets in project: $PROJECT_ID"
    
    echo ""
    printf "%-30s %-20s %-20s %s\n" "NAME" "CREATED" "LABELS" "VERSIONS"
    echo "--------------------------------------------------------------------------------"
    
    gcloud secrets list \
        --project="$PROJECT_ID" \
        --format="table[no-heading](name,createTime:label=CREATED,labels,versionCount)" \
        2>/dev/null | while read -r line; do
        printf "%-30s %s\n" "$line"
    done
    
    echo ""
    log_success "Secrets listed"
}

###############################################################################
# Create Secret
###############################################################################
create_secret() {
    local secret_name="$1"
    local secret_value="${2:-}"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    # Check if secret already exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        log_error "Secret '$secret_name' already exists. Use 'update' to modify it."
        exit 1
    fi
    
    # Get value if not provided
    if [[ -z "$secret_value" ]]; then
        read -s -p "Enter secret value: " secret_value
        echo ""
        
        if [[ -z "$secret_value" ]]; then
            log_error "Secret value cannot be empty"
            exit 1
        fi
    fi
    
    log_info "Creating secret: $secret_name"
    
    echo "$secret_value" | gcloud secrets create "$secret_name" \
        --project="$PROJECT_ID" \
        --replication-policy="automatic" \
        --labels="created-by=manage-secrets,project=sentilyze" \
        --data-file=- \
        --quiet
    
    log_success "Secret '$secret_name' created successfully"
}

###############################################################################
# Update Secret
###############################################################################
update_secret() {
    local secret_name="$1"
    local secret_value="${2:-}"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    # Check if secret exists
    if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        log_error "Secret '$secret_name' does not exist. Use 'create' to create it."
        exit 1
    fi
    
    # Get value if not provided
    if [[ -z "$secret_value" ]]; then
        read -s -p "Enter new secret value: " secret_value
        echo ""
        
        if [[ -z "$secret_value" ]]; then
            log_error "Secret value cannot be empty"
            exit 1
        fi
    fi
    
    log_info "Updating secret: $secret_name"
    
    echo "$secret_value" | gcloud secrets versions add "$secret_name" \
        --project="$PROJECT_ID" \
        --data-file=- \
        --quiet
    
    log_success "Secret '$secret_name' updated successfully"
}

###############################################################################
# Get Secret
###############################################################################
get_secret() {
    local secret_name="$1"
    local version="${2:-latest}"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    log_info "Retrieving secret: $secret_name (version: $version)"
    
    local value
    value=$(gcloud secrets versions access "$version" \
        --secret="$secret_name" \
        --project="$PROJECT_ID" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        echo "$value"
    else
        log_error "Failed to retrieve secret '$secret_name'"
        exit 1
    fi
}

###############################################################################
# List Secret Versions
###############################################################################
list_versions() {
    local secret_name="$1"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    log_info "Listing versions for secret: $secret_name"
    
    echo ""
    printf "%-10s %-20s %-15s %s\n" "VERSION" "CREATED" "STATE" "EXPIRES"
    echo "--------------------------------------------------------------------------------"
    
    gcloud secrets versions list "$secret_name" \
        --project="$PROJECT_ID" \
        --format="table[no-heading](name,createTime,state,expireTime)" \
        2>/dev/null | while read -r line; do
        printf "%-10s %s\n" "$line"
    done
    
    echo ""
}

###############################################################################
# Rotate Secret
###############################################################################
rotate_secret() {
    local secret_name="$1"
    local new_value="${2:-}"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    # Check if secret exists
    if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        log_error "Secret '$secret_name' does not exist"
        exit 1
    fi
    
    log_warning "You are about to rotate secret: $secret_name"
    log_warning "This will create a new version and may affect running services."
    read -p "Continue? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "Rotation cancelled"
        exit 0
    fi
    
    # Get new value if not provided
    if [[ -z "$new_value" ]]; then
        read -s -p "Enter new secret value: " new_value
        echo ""
        
        if [[ -z "$new_value" ]]; then
            log_error "Secret value cannot be empty"
            exit 1
        fi
    fi
    
    log_info "Rotating secret: $secret_name"
    
    echo "$new_value" | gcloud secrets versions add "$secret_name" \
        --project="$PROJECT_ID" \
        --data-file=- \
        --quiet
    
    log_success "Secret '$secret_name' rotated successfully"
    
    # Clean up old versions
    cleanup_versions "$secret_name" 5
}

###############################################################################
# Delete Secret
###############################################################################
delete_secret() {
    local secret_name="$1"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    log_warning "You are about to DELETE secret: $secret_name"
    log_warning "This action is IRREVERSIBLE!"
    read -p "Type the secret name to confirm deletion: " confirm
    
    if [[ "$confirm" != "$secret_name" ]]; then
        log_error "Confirmation failed. Secret name mismatch."
        exit 1
    fi
    
    log_info "Deleting secret: $secret_name"
    
    gcloud secrets delete "$secret_name" \
        --project="$PROJECT_ID" \
        --quiet
    
    log_success "Secret '$secret_name' deleted successfully"
}

###############################################################################
# Clean Up Old Versions
###############################################################################
cleanup_versions() {
    local secret_name="$1"
    local keep_count="${2:-5}"
    
    if [[ -z "$secret_name" ]]; then
        log_error "Secret name is required"
        exit 1
    fi
    
    log_info "Cleaning up old versions for secret: $secret_name"
    log_info "Keeping last $keep_count versions"
    
    # Get all enabled versions (sorted by number)
    local versions
    versions=$(gcloud secrets versions list "$secret_name" \
        --project="$PROJECT_ID" \
        --filter="state=ENABLED" \
        --format="value(name)" \
        --sort-by=name 2>/dev/null)
    
    local version_count
    version_count=$(echo "$versions" | wc -l)
    
    if [[ $version_count -le $keep_count ]]; then
        log_info "Only $version_count version(s) exist, nothing to clean up"
        return
    fi
    
    # Disable old versions
    local versions_to_delete
    versions_to_delete=$(echo "$versions" | head -n -$keep_count)
    
    while IFS= read -r version; do
        if [[ -n "$version" ]]; then
            log_info "Disabling version: $version"
            gcloud secrets versions disable "$version" \
                --secret="$secret_name" \
                --project="$PROJECT_ID" \
                --quiet 2>/dev/null || true
        fi
    done <<< "$versions_to_delete"
    
    log_success "Cleaned up old versions"
}

###############################################################################
# Import Secrets
###############################################################################
import_secrets() {
    local file_path="$1"
    
    if [[ -z "$file_path" ]]; then
        log_error "File path is required"
        exit 1
    fi
    
    if [[ ! -f "$file_path" ]]; then
        log_error "File not found: $file_path"
        exit 1
    fi
    
    log_info "Importing secrets from: $file_path"
    
    # Parse JSON and create/update secrets
    local secrets_json
    secrets_json=$(cat "$file_path")
    
    # Simple parsing (requires jq or similar)
    if command -v jq &> /dev/null; then
        local count=0
        while IFS= read -r secret_name; do
            local secret_value
            secret_value=$(echo "$secrets_json" | jq -r ".secrets.$secret_name")
            
            if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
                update_secret "$secret_name" "$secret_value"
            else
                create_secret "$secret_name" "$secret_value"
            fi
            ((count++))
        done <<< "$(echo "$secrets_json" | jq -r '.secrets | keys[]')"
        
        log_success "Imported $count secrets"
    else
        log_error "jq is required for JSON parsing. Install jq to use this feature."
        exit 1
    fi
}

###############################################################################
# Export Secrets
###############################################################################
export_secrets() {
    local file_path="${1:-sentilyze-secrets-$(date +%Y%m%d-%H%M%S).json}"
    
    log_info "Exporting secrets to: $file_path"
    log_warning "Warning: This will export secret values in plain text!"
    read -p "Continue? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "Export cancelled"
        exit 0
    fi
    
    # Create JSON structure
    local json_output="{\"exported_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"project\": \"$PROJECT_ID\", \"secrets\": {}}"
    
    # Get list of secrets
    local secrets
    secrets=$(gcloud secrets list \
        --project="$PROJECT_ID" \
        --format="value(name)" 2>/dev/null)
    
    if command -v jq &> /dev/null; then
        while IFS= read -r secret_name; do
            if [[ -n "$secret_name" ]]; then
                local secret_value
                secret_value=$(gcloud secrets versions access latest \
                    --secret="$secret_name" \
                    --project="$PROJECT_ID" 2>/dev/null)
                
                # Add to JSON
                json_output=$(echo "$json_output" | jq --arg name "$secret_name" --arg value "$secret_value" '.secrets[$name] = $value')
            fi
        done <<< "$secrets"
        
        echo "$json_output" > "$file_path"
        chmod 600 "$file_path"
        log_success "Exported secrets to $file_path"
    else
        log_error "jq is required for JSON parsing. Install jq to use this feature."
        exit 1
    fi
}

###############################################################################
# Main Execution
###############################################################################
main() {
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        list)
            list_secrets
            ;;
        create)
            create_secret "$@"
            ;;
        update)
            update_secret "$@"
            ;;
        get)
            get_secret "$@"
            ;;
        versions)
            list_versions "$@"
            ;;
        rotate)
            rotate_secret "$@"
            ;;
        delete)
            delete_secret "$@"
            ;;
        cleanup)
            cleanup_versions "$@"
            ;;
        import)
            import_secrets "$@"
            ;;
        export)
            export_secrets "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
