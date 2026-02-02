#!/bin/bash
###############################################################################
# Script: setup-gcp.sh
# Description: Initial GCP project setup for Sentilyze
# Usage: ./setup-gcp.sh [project-id]
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ID="${1:-}"
REGION="${GCP_REGION:-us-central1}"
BILLING_ACCOUNT="${GCP_BILLING_ACCOUNT:-}"

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
# Validate Input
###############################################################################
validate_input() {
    if [[ -z "$PROJECT_ID" ]]; then
        log_error "Project ID is required"
        echo "Usage: $0 <project-id>"
        echo ""
        echo "Example:"
        echo "  $0 sentilyze-v5-clean"
        exit 1
    fi
    
    # Validate project ID format
    if [[ ! "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{5,29}$ ]]; then
        log_error "Invalid project ID format. Must be 6-30 characters, start with letter, use only lowercase letters, numbers, and hyphens."
        exit 1
    fi
}

###############################################################################
# Check Prerequisites
###############################################################################
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it from https://cloud.google.com/sdk"
        exit 1
    fi
    
    if ! gcloud auth print-access-token &> /dev/null; then
        log_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    log_success "Prerequisites met"
}

###############################################################################
# Create or Select Project
###############################################################################
setup_project() {
    log_info "Setting up GCP project: $PROJECT_ID"
    
    # Check if project exists
    if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        log_warning "Project $PROJECT_ID already exists"
    else
        log_info "Creating new project: $PROJECT_ID"
        gcloud projects create "$PROJECT_ID" --name="Sentilyze - ${PROJECT_ID}"
        log_success "Project created"
    fi
    
    # Set as current project
    gcloud config set project "$PROJECT_ID"
    
    # Link billing account if provided
    if [[ -n "$BILLING_ACCOUNT" ]]; then
        log_info "Linking billing account..."
        gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
        log_success "Billing account linked"
    else
        log_warning "No billing account provided. You must manually link a billing account."
    fi
}

###############################################################################
# Enable APIs
###############################################################################
enable_apis() {
    log_info "Enabling required GCP APIs..."
    
    APIS=(
        "run.googleapis.com"              # Cloud Run
        "containerregistry.googleapis.com" # Container Registry
        "artifactregistry.googleapis.com"  # Artifact Registry
        "cloudbuild.googleapis.com"        # Cloud Build
        "pubsub.googleapis.com"            # Pub/Sub
        "bigquery.googleapis.com"          # BigQuery
        "secretmanager.googleapis.com"     # Secret Manager
        "cloudsql.googleapis.com"          # Cloud SQL
        "monitoring.googleapis.com"        # Cloud Monitoring
        "logging.googleapis.com"           # Cloud Logging
        "cloudtrace.googleapis.com"        # Cloud Trace
        "firestore.googleapis.com"         # Firestore
        "storage.googleapis.com"           # Cloud Storage
    )
    
    for api in "${APIS[@]}"; do
        log_info "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    done
    
    log_success "All APIs enabled"
}

###############################################################################
# Create Service Accounts
###############################################################################
create_service_accounts() {
    log_info "Creating service accounts..."
    
    # API Service Account
    if ! gcloud iam service-accounts describe "sentilyze-api@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        gcloud iam service-accounts create sentilyze-api \
            --display-name="Sentilyze API Service Account" \
            --description="Service account for Sentilyze API service"
        log_success "Created sentilyze-api service account"
    fi
    
    # Worker Service Account
    if ! gcloud iam service-accounts describe "sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        gcloud iam service-accounts create sentilyze-worker \
            --display-name="Sentilyze Worker Service Account" \
            --description="Service account for Sentilyze background worker service"
        log_success "Created sentilyze-worker service account"
    fi
    
    # Scheduler Service Account
    if ! gcloud iam service-accounts describe "sentilyze-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        gcloud iam service-accounts create sentilyze-scheduler \
            --display-name="Sentilyze Scheduler Service Account" \
            --description="Service account for Sentilyze scheduler service"
        log_success "Created sentilyze-scheduler service account"
    fi
    
    # Cloud Build Service Account (uses default)
    log_success "All service accounts created"
}

###############################################################################
# Setup IAM Permissions
###############################################################################
setup_iam_permissions() {
    log_info "Setting up IAM permissions..."
    
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    
    # API Service Account permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-api@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/bigquery.dataViewer" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-api@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/pubsub.publisher" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-api@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None
    
    # Worker Service Account permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/bigquery.dataEditor" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/pubsub.subscriber" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/pubsub.publisher" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/storage.objectViewer" \
        --condition=None
    
    # Scheduler Service Account permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/pubsub.publisher" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:sentilyze-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None
    
    # Cloud Build service account permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/run.admin" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/storage.admin" \
        --condition=None
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/artifactregistry.admin" \
        --condition=None
    
    log_success "IAM permissions configured"
}

###############################################################################
# Configure Secret Manager
###############################################################################
configure_secret_manager() {
    log_info "Configuring Secret Manager..."
    
    # Create placeholder secrets (actual values need to be set separately)
    SECRETS=(
        "database-url:PostgreSQL connection string"
        "redis-url:Redis connection string"
        "jwt-secret:JWT signing secret"
        "api-key:Internal API key"
        "openai-api-key:OpenAI API key"
        "google-cloud-api-key:Google Cloud API key"
    )
    
    for secret_info in "${SECRETS[@]}"; do
        IFS=':' read -r secret_name description <<< "$secret_info"
        
        # Check if secret exists
        if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
            log_info "Creating secret: $secret_name"
            echo "placeholder" | gcloud secrets create "$secret_name" \
                --project="$PROJECT_ID" \
                --replication-policy="automatic" \
                --labels="environment=all,created-by=setup-script" \
                --data-file=- \
                --quiet
            log_warning "Secret $secret_name created with placeholder value. Update it with real value!"
        else
            log_info "Secret $secret_name already exists"
        fi
    done
    
    log_success "Secret Manager configured"
    log_warning "Remember to update secret values with actual credentials!"
}

###############################################################################
# Create Cloud Storage Buckets
###############################################################################
create_storage_buckets() {
    log_info "Creating Cloud Storage buckets..."
    
    BUCKETS=(
        "${PROJECT_ID}-data:Data storage"
        "${PROJECT_ID}-backups:Database backups"
        "${PROJECT_ID}-artifacts:Build artifacts"
    )
    
    for bucket_info in "${BUCKETS[@]}"; do
        IFS=':' read -r bucket_name description <<< "$bucket_info"
        
        if ! gsutil ls -b "gs://${bucket_name}/" &> /dev/null; then
            gsutil mb -p "$PROJECT_ID" -l "$REGION" -c standard "gs://${bucket_name}/"
            log_success "Created bucket: $bucket_name"
        else
            log_info "Bucket $bucket_name already exists"
        fi
    done
    
    log_success "Storage buckets created"
}

###############################################################################
# Create Artifact Registry Repository
###############################################################################
create_artifact_registry() {
    log_info "Creating Artifact Registry repository..."
    
    if ! gcloud artifacts repositories describe sentilyze \
        --location="$REGION" \
        --project="$PROJECT_ID" &> /dev/null; then
        
        gcloud artifacts repositories create sentilyze \
            --repository-format=docker \
            --location="$REGION" \
            --description="Docker images for Sentilyze services"
        
        log_success "Created Artifact Registry repository"
    else
        log_info "Artifact Registry repository already exists"
    fi
}

###############################################################################
# Setup Cloud Build Triggers
###############################################################################
setup_cloud_build() {
    log_info "Setting up Cloud Build triggers..."
    
    # Check if trigger already exists
    if ! gcloud builds triggers describe sentilyze-deploy \
        --project="$PROJECT_ID" &> /dev/null; then
        
        log_warning "Cloud Build trigger not created automatically."
        log_info "To create manually, run:"
        echo "  gcloud builds triggers create github \\"
        echo "    --project=$PROJECT_ID \\"
        echo "    --repo-name=sentilyze \\"
        echo "    --repo-owner=your-org \\"
        echo "    --branch-pattern='^main$' \\"
        echo "    --build-config=cloudbuild.yaml \\"
        echo "    --name=sentilyze-deploy"
    else
        log_info "Cloud Build trigger already exists"
    fi
}

###############################################################################
# Setup VPC Connector (optional)
###############################################################################
setup_vpc_connector() {
    log_info "Setting up VPC Connector (optional)..."
    
    log_warning "VPC Connector setup skipped. Configure manually if needed for private connectivity."
}

###############################################################################
# Print Summary
###############################################################################
print_summary() {
    echo ""
    log_success "========================================="
    log_success "GCP Setup Complete!"
    log_success "========================================="
    echo ""
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"
    echo ""
    log_info "Next steps:"
    log_info "  1. Update secret values: ./manage-secrets.sh update"
    log_info "  2. Deploy services: ./deploy.sh"
    log_info "  3. Setup BigQuery: python tools/bq_setup.py"
    log_info "  4. Setup Pub/Sub: python tools/pubsub_setup.py"
    echo ""
    log_info "Useful commands:"
    echo "  gcloud config set project $PROJECT_ID"
    echo "  gcloud services list --enabled"
    echo "  gcloud iam service-accounts list"
    echo ""
}

###############################################################################
# Main Execution
###############################################################################
main() {
    log_info "========================================="
    log_info "Sentilyze GCP Setup"
    log_info "Project: ${PROJECT_ID:-Not specified}"
    log_info "========================================="
    
    validate_input
    check_prerequisites
    setup_project
    enable_apis
    create_service_accounts
    setup_iam_permissions
    configure_secret_manager
    create_storage_buckets
    create_artifact_registry
    setup_cloud_build
    setup_vpc_connector
    print_summary
}

# Run main function
main "$@"
