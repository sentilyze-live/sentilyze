#!/bin/bash
# Agent OS - GCP Deployment Script
# 
# This script deploys the Agent OS system to Google Cloud Platform
#
# Usage: ./scripts/gcp-deploy.sh [environment]
#   environment: development (default) | staging | production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-development}
PROJECT_ID="sentilyze-v5-clean"
REGION="us-central1"
SERVICE_NAME="agent-os-core"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Agent OS - GCP Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Project ID: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Region: ${YELLOW}${REGION}${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Check docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites met${NC}"
echo ""

# Set GCP project
echo -e "${BLUE}Setting GCP project...${NC}"
gcloud config set project ${PROJECT_ID}
echo -e "${GREEN}✓ Project set${NC}"
echo ""

# Enable required APIs
echo -e "${BLUE}Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    artifactregistry.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com \
    pubsub.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    --quiet
echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Build and push Docker image
echo -e "${BLUE}Building Docker image...${NC}"
cd services/agent-os-core

docker build \
    -t ${IMAGE_NAME}:latest \
    -t ${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S) \
    -f Dockerfile \
    ../..

echo -e "${GREEN}✓ Image built${NC}"
echo ""

# Push to Container Registry
echo -e "${BLUE}Pushing to Container Registry...${NC}"
docker push ${IMAGE_NAME}:latest
echo -e "${GREEN}✓ Image pushed${NC}"
echo ""

cd ../..

# Deploy to Cloud Run
echo -e "${BLUE}Deploying to Cloud Run...${NC}"

gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --concurrency 80 \
    --max-instances 5 \
    --min-instances 1 \
    --timeout 300 \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT}" \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="GCP_REGION=${REGION}" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --set-env-vars="CACHE_TYPE=firestore" \
    --set-secrets="MOONSHOT_API_KEY=moonshot-api-key:latest" \
    --set-secrets="HIGGSFIELD_API_KEY=higgsfield-api-key:latest" \
    --set-secrets="TELEGRAM_BOT_TOKEN=telegram-bot-token:latest" \
    --set-secrets="TELEGRAM_CHAT_ID=telegram-chat-id:latest" \
    --quiet

echo -e "${GREEN}✓ Deployed to Cloud Run${NC}"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo ""

# Setup Cloud Scheduler for agent runs
echo -e "${BLUE}Setting up Cloud Scheduler...${NC}"

# SCOUT - Every 6 hours
gcloud scheduler jobs create http ${SERVICE_NAME}-scout \
    --schedule="0 */6 * * *" \
    --uri="${SERVICE_URL}/agents/scout/run" \
    --http-method=POST \
    --time-zone="UTC" \
    --attempt-deadline=300s \
    --quiet 2>/dev/null || echo "SCOUT scheduler already exists"

# ELON - Daily
gcloud scheduler jobs create http ${SERVICE_NAME}-elon \
    --schedule="0 9 * * *" \
    --uri="${SERVICE_URL}/agents/elon/run" \
    --http-method=POST \
    --time-zone="UTC" \
    --attempt-deadline=300s \
    --quiet 2>/dev/null || echo "ELON scheduler already exists"

# SETH - Weekly (Mondays)
gcloud scheduler jobs create http ${SERVICE_NAME}-seth \
    --schedule="0 10 * * 1" \
    --uri="${SERVICE_URL}/agents/seth/run" \
    --http-method=POST \
    --time-zone="UTC" \
    --attempt-deadline=600s \
    --quiet 2>/dev/null || echo "SETH scheduler already exists"

# ZARA - Every 30 minutes
gcloud scheduler jobs create http ${SERVICE_NAME}-zara \
    --schedule="*/30 * * * *" \
    --uri="${SERVICE_URL}/agents/zara/run" \
    --http-method=POST \
    --time-zone="UTC" \
    --attempt-deadline=180s \
    --quiet 2>/dev/null || echo "ZARA scheduler already exists"

# ECE - Daily
gcloud scheduler jobs create http ${SERVICE_NAME}-ece \
    --schedule="0 8 * * *" \
    --uri="${SERVICE_URL}/agents/ece/run" \
    --http-method=POST \
    --time-zone="UTC" \
    --attempt-deadline=600s \
    --quiet 2>/dev/null || echo "ECE scheduler already exists"

echo -e "${GREEN}✓ Cloud Scheduler jobs created${NC}"
echo ""

# Setup Firestore
echo -e "${BLUE}Setting up Firestore...${NC}"
gcloud firestore databases create --region=${REGION} --quiet 2>/dev/null || echo "Firestore already exists"
echo -e "${GREEN}✓ Firestore ready${NC}"
echo ""

# Setup Pub/Sub topics
echo -e "${BLUE}Setting up Pub/Sub topics...${NC}"
gcloud pubsub topics create agent-os-trends --quiet 2>/dev/null || true
gcloud pubsub topics create agent-os-content --quiet 2>/dev/null || true
gcloud pubsub topics create agent-os-experiments --quiet 2>/dev/null || true
gcloud pubsub topics create agent-os-community --quiet 2>/dev/null || true
gcloud pubsub topics create agent-os-visuals --quiet 2>/dev/null || true
echo -e "${GREEN}✓ Pub/Sub topics created${NC}"
echo ""

# Deployment summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Service: ${YELLOW}${SERVICE_NAME}${NC}"
echo -e "URL: ${YELLOW}${SERVICE_URL}${NC}"
echo ""
echo -e "Agent Endpoints:"
echo -e "  - SCOUT: ${SERVICE_URL}/agents/scout/run"
echo -e "  - ELON: ${SERVICE_URL}/agents/elon/run"
echo -e "  - SETH: ${SERVICE_URL}/agents/seth/run"
echo -e "  - ZARA: ${SERVICE_URL}/agents/zara/run"
echo -e "  - ECE: ${SERVICE_URL}/agents/ece/run"
echo ""
echo -e "Health Check: ${SERVICE_URL}/health"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Test the deployment: curl ${SERVICE_URL}/health"
echo "  2. Run a test agent: curl -X POST ${SERVICE_URL}/agents/scout/run"
echo "  3. Check logs: gcloud logging tail 'resource.type=cloud_run_revision'"
echo ""
