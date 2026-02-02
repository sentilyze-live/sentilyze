#!/bin/bash
###############################################################################
# Script: deploy.sh
# Description: Main deployment script for Sentilyze on GCP
# Usage: ./deploy.sh [environment] [version]
#   environment: dev|staging|prod (default: dev)
#   version: version tag (default: git-sha)
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-dev}"
VERSION="${2:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"
# NOTE: The default pattern creates project names like sentilyze-dev, sentilyze-staging, sentilyze-prod
# For the current project 'sentilyze-v5-clean', explicitly set GCP_PROJECT_ID environment variable
PROJECT_ID="${GCP_PROJECT_ID:-sentilyze-${ENVIRONMENT}}"
REGION="${GCP_REGION:-us-central1}"

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

# Error handler
error_handler() {
    log_error "Deployment failed at line $1"
    exit 1
}

trap 'error_handler $LINENO' ERR

###############################################################################
# Check Prerequisites
###############################################################################
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check gcloud authentication
    if ! gcloud auth print-access-token &> /dev/null; then
        log_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    # Check project configuration
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [[ "$CURRENT_PROJECT" != "$PROJECT_ID" ]]; then
        log_warning "Switching gcloud project from $CURRENT_PROJECT to $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
    
    log_success "All prerequisites met"
}

###############################################################################
# Build and Push Docker Images
###############################################################################
build_and_push() {
    log_info "Building and pushing Docker images..."
    
    # Configure Docker for GCR
    gcloud auth configure-docker "gcr.io" --quiet 2>/dev/null || true
    
    # Build images
    cd "$PROJECT_ROOT"
    
    SERVICES=("api" "worker" "scheduler")
    for service in "${SERVICES[@]}"; do
        log_info "Building $service service..."
        
        IMAGE_NAME="gcr.io/${PROJECT_ID}/sentilyze-${service}:${VERSION}"
        
        docker build \
            -t "$IMAGE_NAME" \
            -f "docker/${service}.Dockerfile" \
            --build-arg VERSION="$VERSION" \
            --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            .
        
        log_info "Pushing $service image to GCR..."
        docker push "$IMAGE_NAME"
        
        # Also tag as latest for this environment
        LATEST_TAG="gcr.io/${PROJECT_ID}/sentilyze-${service}:${ENVIRONMENT}-latest"
        docker tag "$IMAGE_NAME" "$LATEST_TAG"
        docker push "$LATEST_TAG"
        
        log_success "Built and pushed $service:$VERSION"
    done
    
    log_success "All Docker images built and pushed successfully"
}

###############################################################################
# Deploy to Cloud Run
###############################################################################
deploy_cloud_run() {
    log_info "Deploying services to Cloud Run..."
    
    # Common Cloud Run settings
    COMMON_FLAGS="--platform managed \
        --region ${REGION} \
        --project ${PROJECT_ID} \
        --set-env-vars=ENVIRONMENT=${ENVIRONMENT},VERSION=${VERSION}"
    
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        COMMON_FLAGS="${COMMON_FLAGS} --min-instances=2 --max-instances=100"
    else
        COMMON_FLAGS="${COMMON_FLAGS} --min-instances=0 --max-instances=10"
    fi
    
    # Deploy API service
    log_info "Deploying API service..."
    gcloud run deploy sentilyze-api-${ENVIRONMENT} \
        --image "gcr.io/${PROJECT_ID}/sentilyze-api:${VERSION}" \
        --service-account "sentilyze-api@${PROJECT_ID}.iam.gserviceaccount.com" \
        --memory "1Gi" \
        --cpu "1" \
        --timeout "300" \
        --concurrency "80" \
        --port "8080" \
        ${COMMON_FLAGS} \
        --set-env-vars^CLOUD_RUN_SERVICE_NAME=sentilyze-api-${ENVIRONMENT}
    
    log_success "API service deployed"
    
    # Deploy Worker service
    log_info "Deploying Worker service..."
    gcloud run deploy sentilyze-worker-${ENVIRONMENT} \
        --image "gcr.io/${PROJECT_ID}/sentilyze-worker:${VERSION}" \
        --service-account "sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --memory "2Gi" \
        --cpu "2" \
        --timeout "900" \
        --concurrency "1" \
        ${COMMON_FLAGS} \
        --set-env-vars^CLOUD_RUN_SERVICE_NAME=sentilyze-worker-${ENVIRONMENT} \
        --no-allow-unauthenticated
    
    log_success "Worker service deployed"
    
    # Deploy Scheduler service
    log_info "Deploying Scheduler service..."
    gcloud run deploy sentilyze-scheduler-${ENVIRONMENT} \
        --image "gcr.io/${PROJECT_ID}/sentilyze-scheduler:${VERSION}" \
        --service-account "sentilyze-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
        --memory "512Mi" \
        --cpu "0.5" \
        --timeout "300" \
        --concurrency "1" \
        ${COMMON_FLAGS} \
        --set-env-vars^CLOUD_RUN_SERVICE_NAME=sentilyze-scheduler-${ENVIRONMENT} \
        --no-allow-unauthenticated
    
    log_success "Scheduler service deployed"
    
    log_success "All services deployed to Cloud Run"
}

###############################################################################
# Configure Pub/Sub
###############################################################################
configure_pubsub() {
    log_info "Configuring Pub/Sub..."
    
    cd "$PROJECT_ROOT"
    python tools/pubsub_setup.py --project "$PROJECT_ID" --environment "$ENVIRONMENT"
    
    log_success "Pub/Sub configured"
}

###############################################################################
# Setup BigQuery
###############################################################################
setup_bigquery() {
    log_info "Setting up BigQuery..."
    
    cd "$PROJECT_ROOT"
    python tools/bq_setup.py --project "$PROJECT_ID" --environment "$ENVIRONMENT"
    
    log_success "BigQuery configured"
}

###############################################################################
# Run Migrations
###############################################################################
run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    python tools/migrate-db.py --environment "$ENVIRONMENT" migrate
    
    log_success "Migrations completed"
}

###############################################################################
# Health Check
###############################################################################
health_check() {
    log_info "Running health checks..."
    
    cd "$PROJECT_ROOT"
    ./scripts/health-check.sh --environment "$ENVIRONMENT"
    
    log_success "Health checks passed"
}

###############################################################################
# Main Execution
###############################################################################
main() {
    log_info "========================================="
    log_info "Sentilyze Deployment - ${ENVIRONMENT}"
    log_info "Version: ${VERSION}"
    log_info "Project: ${PROJECT_ID}"
    log_info "Region: ${REGION}"
    log_info "========================================="
    
    # Confirm deployment for production
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        log_warning "You are about to deploy to PRODUCTION!"
        read -p "Are you sure? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    # Execute deployment steps
    check_prerequisites
    build_and_push
    deploy_cloud_run
    configure_pubsub
    setup_bigquery
    run_migrations
    health_check
    
    log_success "========================================="
    log_success "Deployment completed successfully!"
    log_success "========================================="
    
    # Display service URLs
    echo ""
    log_info "Service URLs:"
    gcloud run services list --platform managed --region "$REGION" --project "$PROJECT_ID" \
        --format="table[box,margin=3](metadata.name:label=SERVICES,status.url:label=URL)"
}

# Run main function
main "$@"
