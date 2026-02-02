#!/bin/bash
###############################################################################
# Script: health-check.sh
# Description: Health check script for Sentilyze services
# Usage: ./health-check.sh [--environment <env>] [--verbose] [--json]
###############################################################################

set -uo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-dev}"
VERBOSE=false
JSON_OUTPUT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --json|-j)
            JSON_OUTPUT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --environment, -e <env>  Environment (dev/staging/prod)"
            echo "  --verbose, -v           Enable verbose output"
            echo "  --json, -j              Output results as JSON"
            echo "  --help, -h              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors for output (disabled for JSON)
if [[ "$JSON_OUTPUT" == "false" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Results tracking
declare -A SERVICE_STATUS
declare -A SERVICE_DETAILS
declare -A SERVICE_RESPONSE_TIME
OVERALL_STATUS="healthy"

# Logging functions
log_info() {
    [[ "$JSON_OUTPUT" == "false" ]] && echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    [[ "$JSON_OUTPUT" == "false" ]] && echo -e "${GREEN}[PASS]${NC} $1"
}

log_warning() {
    [[ "$JSON_OUTPUT" == "false" ]] && echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    [[ "$JSON_OUTPUT" == "false" ]] && echo -e "${RED}[FAIL]${NC} $1"
}

###############################################################################
# Check API Service
###############################################################################
check_api() {
    local service_name="api"
    local endpoint
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        endpoint="http://localhost:8080/health"
    else
        # Get Cloud Run URL
        endpoint=$(gcloud run services describe "sentilyze-api-${ENVIRONMENT}" \
            --platform managed \
            --region us-central1 \
            --format='value(status.url)' 2>/dev/null)
        endpoint="${endpoint}/health"
    fi
    
    if [[ -z "$endpoint" ]] || [[ "$endpoint" == "/health" ]]; then
        SERVICE_STATUS[$service_name]="unknown"
        SERVICE_DETAILS[$service_name]="Service URL not found"
        OVERALL_STATUS="degraded"
        return
    fi
    
    local start_time end_time duration
    start_time=$(date +%s%N)
    
    local response
    response=$(curl -s -w "\n%{http_code}" "$endpoint" --max-time 10 2>/dev/null)
    
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
    
    SERVICE_RESPONSE_TIME[$service_name]="${duration}ms"
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | head -n-1)
    
    if [[ "$http_code" == "200" ]]; then
        SERVICE_STATUS[$service_name]="healthy"
        SERVICE_DETAILS[$service_name]="OK (${duration}ms)"
        log_success "API service is healthy (${duration}ms)"
    else
        SERVICE_STATUS[$service_name]="unhealthy"
        SERVICE_DETAILS[$service_name]="HTTP $http_code"
        OVERALL_STATUS="unhealthy"
        log_error "API service is unhealthy (HTTP $http_code)"
    fi
}

###############################################################################
# Check Worker Service
###############################################################################
check_worker() {
    local service_name="worker"
    local endpoint
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        endpoint="http://localhost:8081/health"
    else
        endpoint=$(gcloud run services describe "sentilyze-worker-${ENVIRONMENT}" \
            --platform managed \
            --region us-central1 \
            --format='value(status.url)' 2>/dev/null)
        endpoint="${endpoint}/health"
    fi
    
    if [[ -z "$endpoint" ]] || [[ "$endpoint" == "/health" ]]; then
        SERVICE_STATUS[$service_name]="unknown"
        SERVICE_DETAILS[$service_name]="Service URL not found"
        OVERALL_STATUS="degraded"
        return
    fi
    
    local start_time end_time duration
    start_time=$(date +%s%N)
    
    local response
    response=$(curl -s -w "\n%{http_code}" "$endpoint" --max-time 10 2>/dev/null)
    
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))
    
    SERVICE_RESPONSE_TIME[$service_name]="${duration}ms"
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]]; then
        SERVICE_STATUS[$service_name]="healthy"
        SERVICE_DETAILS[$service_name]="OK (${duration}ms)"
        log_success "Worker service is healthy (${duration}ms)"
    else
        SERVICE_STATUS[$service_name]="unhealthy"
        SERVICE_DETAILS[$service_name]="HTTP $http_code"
        OVERALL_STATUS="unhealthy"
        log_error "Worker service is unhealthy (HTTP $http_code)"
    fi
}

###############################################################################
# Check Database
###############################################################################
check_database() {
    local service_name="database"
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        # Check PostgreSQL locally
        if docker-compose ps postgres | grep -q "Up"; then
            SERVICE_STATUS[$service_name]="healthy"
            SERVICE_DETAILS[$service_name]="PostgreSQL is running"
            log_success "Database is healthy"
        else
            SERVICE_STATUS[$service_name]="unhealthy"
            SERVICE_DETAILS[$service_name]="PostgreSQL not responding"
            OVERALL_STATUS="unhealthy"
            log_error "Database is unhealthy"
        fi
    else
        # For cloud, check via API or Cloud SQL
        SERVICE_STATUS[$service_name]="unknown"
        SERVICE_DETAILS[$service_name]="Check via Cloud SQL console"
        log_warning "Database health check skipped (check Cloud SQL console)"
    fi
}

###############################################################################
# Check Firestore
###############################################################################
check_firestore() {
    local service_name="firestore"
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        # Check Firestore emulator locally
        if docker-compose ps firestore-emulator | grep -q "Up"; then
            SERVICE_STATUS[$service_name]="healthy"
            SERVICE_DETAILS[$service_name]="Firestore emulator is running"
            log_success "Firestore is healthy"
        else
            SERVICE_STATUS[$service_name]="unhealthy"
            SERVICE_DETAILS[$service_name]="Firestore emulator not responding"
            OVERALL_STATUS="unhealthy"
            log_error "Firestore is unhealthy"
        fi
    else
        # For cloud, check via Firestore API
        local project_id
        project_id=$(gcloud config get-value project 2>/dev/null)
        
        if gcloud firestore databases list --project="$project_id" &> /dev/null; then
            SERVICE_STATUS[$service_name]="healthy"
            SERVICE_DETAILS[$service_name]="Firestore API responding"
            log_success "Firestore is healthy"
        else
            SERVICE_STATUS[$service_name]="unknown"
            SERVICE_DETAILS[$service_name]="Unable to verify"
        fi
    fi
}

###############################################################################
# Check Pub/Sub
###############################################################################
check_pubsub() {
    local service_name="pubsub"
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        # For local, check if emulator is running
        if curl -s http://localhost:8085/v1/projects/test-project/topics 2>/dev/null | grep -q "topics"; then
            SERVICE_STATUS[$service_name]="healthy"
            SERVICE_DETAILS[$service_name]="Pub/Sub emulator is running"
            log_success "Pub/Sub is healthy"
        else
            SERVICE_STATUS[$service_name]="unknown"
            SERVICE_DETAILS[$service_name]="Pub/Sub emulator not detected"
        fi
    else
        # Check Pub/Sub via gcloud
        local project_id
        project_id=$(gcloud config get-value project 2>/dev/null)
        
        if gcloud pubsub topics list --project="$project_id" &> /dev/null; then
            SERVICE_STATUS[$service_name]="healthy"
            SERVICE_DETAILS[$service_name]="Pub/Sub API responding"
            log_success "Pub/Sub is healthy"
        else
            SERVICE_STATUS[$service_name]="unknown"
            SERVICE_DETAILS[$service_name]="Unable to verify"
        fi
    fi
}

###############################################################################
# Check BigQuery
###############################################################################
check_bigquery() {
    local service_name="bigquery"
    
    local project_id
    project_id=$(gcloud config get-value project 2>/dev/null)
    
    if gcloud bq datasets list --project="$project_id" &> /dev/null; then
        SERVICE_STATUS[$service_name]="healthy"
        SERVICE_DETAILS[$service_name]="BigQuery API responding"
        log_success "BigQuery is healthy"
    else
        SERVICE_STATUS[$service_name]="unknown"
        SERVICE_DETAILS[$service_name]="Unable to verify"
    fi
}

###############################################################################
# Output JSON Results
###############################################################################
output_json() {
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo "{"
    echo "  \"timestamp\": \"$timestamp\","
    echo "  \"environment\": \"$ENVIRONMENT\","
    echo "  \"overall_status\": \"$OVERALL_STATUS\","
    echo "  \"services\": {"
    
    local first=true
    for service in api worker database firestore pubsub bigquery; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        
        local status="${SERVICE_STATUS[$service]:-unknown}"
        local details="${SERVICE_DETAILS[$service]:-N/A}"
        local response_time="${SERVICE_RESPONSE_TIME[$service]:-N/A}"
        
        echo -n "    \"$service\": {"
        echo -n "\"status\": \"$status\", "
        echo -n "\"details\": \"$details\", "
        echo -n "\"response_time\": \"$response_time\""
        echo -n "}"
    done
    
    echo ""
    echo "  }"
    echo "}"
}

###############################################################################
# Output Summary
###############################################################################
output_summary() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json
        return
    fi
    
    echo ""
    echo "========================================="
    echo "Health Check Summary"
    echo "Environment: $ENVIRONMENT"
    echo "========================================="
    echo ""
    
    printf "%-15s %-10s %s\n" "Service" "Status" "Details"
    echo "-----------------------------------------"
    
    for service in api worker database firestore pubsub bigquery; do
        local status="${SERVICE_STATUS[$service]:-unknown}"
        local details="${SERVICE_DETAILS[$service]:-N/A}"
        
        local color="$NC"
        case "$status" in
            healthy)
                color="$GREEN"
                ;;
            unhealthy)
                color="$RED"
                ;;
            *)
                color="$YELLOW"
                ;;
        esac
        
        printf "%-15s ${color}%-10s${NC} %s\n" "$service" "$status" "$details"
    done
    
    echo ""
    echo "========================================="
    
    if [[ "$OVERALL_STATUS" == "healthy" ]]; then
        echo -e "${GREEN}Overall Status: HEALTHY${NC}"
    elif [[ "$OVERALL_STATUS" == "degraded" ]]; then
        echo -e "${YELLOW}Overall Status: DEGRADED${NC}"
    else
        echo -e "${RED}Overall Status: UNHEALTHY${NC}"
    fi
    echo "========================================="
}

###############################################################################
# Send Alert (if unhealthy)
###############################################################################
send_alert() {
    if [[ "$OVERALL_STATUS" != "healthy" ]]; then
        # This is where you would integrate with PagerDuty, Slack, etc.
        log_warning "Unhealthy services detected. Consider sending alerts."
        
        if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
            # Send Slack notification
            local message="Sentilyze Health Check Alert: $OVERALL_STATUS services detected in $ENVIRONMENT"
            curl -s -X POST -H 'Content-type: application/json' \
                --data "{\"text\":\"$message\"}" \
                "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || true
        fi
    fi
}

###############################################################################
# Main Execution
###############################################################################
main() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        log_info "Running health checks for environment: $ENVIRONMENT"
    fi
    
    check_api
    check_worker
    check_database
    check_firestore
    check_pubsub
    check_bigquery
    
    output_summary
    send_alert
    
    # Exit with appropriate code
    if [[ "$OVERALL_STATUS" == "unhealthy" ]]; then
        exit 1
    elif [[ "$OVERALL_STATUS" == "degraded" ]]; then
        exit 2
    else
        exit 0
    fi
}

# Run main function
main "$@"
