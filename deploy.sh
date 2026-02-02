#!/bin/bash
# Sentilyze AI Agent Squad - Deployment Script
# This script deploys the updated system with terminology fixes and bilingual support

set -e  # Exit on error

echo "🚀 Sentilyze AI Agent Deployment Script"
echo "========================================"
echo ""

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-gcp-project-id"}
REGION=${GCP_REGION:-"us-central1"}
ENVIRONMENT=${ENV:-"dev"}

echo "📋 Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Environment: $ENVIRONMENT"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Pre-deployment checks
echo "🔍 Pre-deployment Checks"
echo "------------------------"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi
print_status "gcloud CLI found"

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found. Please install Terraform."
    exit 1
fi
print_status "Terraform found"

# Check authentication
echo ""
echo "🔐 Checking GCP Authentication..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1
if [ $? -ne 0 ]; then
    print_error "Not authenticated to GCP. Run: gcloud auth login"
    exit 1
fi
print_status "Authenticated to GCP"

# Set project
gcloud config set project $PROJECT_ID
print_status "Project set to $PROJECT_ID"

echo ""
echo "📦 Phase 1: Infrastructure (Terraform)"
echo "---------------------------------------"
cd infrastructure/terraform

# Initialize terraform
terraform init
print_status "Terraform initialized"

# Plan
terraform plan -out=tfplan
print_status "Terraform plan created"

# Apply
print_warning "About to apply Terraform changes. This will create cloud resources."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply tfplan
    print_status "Terraform applied successfully"
else
    print_error "Deployment cancelled"
    exit 1
fi

cd ../..

echo ""
echo "⚙️ Phase 2: Deploy Cloud Function"
echo "----------------------------------"
cd services/agent-orchestrator

# Install dependencies locally for testing
pip install -r requirements.txt -q
print_status "Dependencies installed"

# Syntax check
python -m py_compile src/main.py
python -m py_compile src/agents/*.py
python -m py_compile src/utils/*.py
print_status "Syntax check passed"

echo ""
print_warning "Deploying Cloud Function..."
gcloud functions deploy agent-orchestrator \
  --runtime python311 \
  --trigger-http \
  --entry-point handle_request \
  --memory 512MB \
  --timeout 60s \
  --max-instances 50 \
  --region $REGION \
  --source . \
  --service-account sentilyze-ai-agents@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=$PROJECT_ID,REGION=$REGION,ENVIRONMENT=$ENVIRONMENT \
  --allow-unauthenticated \
  --quiet

print_status "Cloud Function deployed"

# Get function URL
FUNCTION_URL=$(gcloud functions describe agent-orchestrator --region=$REGION --format="value(status.url)")
print_status "Function URL: $FUNCTION_URL"

cd ../..

echo ""
echo "🌐 Phase 3: Deploy Cloud Run (API Gateway)"
echo "-------------------------------------------"
cd services/agent-gateway

# Build and deploy
gcloud run deploy agent-gateway \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --service-account sentilyze-ai-agents@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars AGENT_ORCHESTRATOR_URL=$FUNCTION_URL,ENVIRONMENT=$ENVIRONMENT \
  --quiet

print_status "Cloud Run service deployed"

# Get service URL
SERVICE_URL=$(gcloud run services describe agent-gateway --region=$REGION --format="value(status.url)")
print_status "API Gateway URL: $SERVICE_URL"

cd ../..

echo ""
echo "🧪 Phase 4: Post-Deployment Tests"
echo "----------------------------------"

# Test health endpoint
echo "Testing health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/health)
if [ $HEALTH_STATUS -eq 200 ]; then
    print_status "Health check passed (HTTP 200)"
else
    print_error "Health check failed (HTTP $HEALTH_STATUS)"
fi

# Test agents endpoint
echo "Testing agents endpoint..."
AGENTS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/agents)
if [ $AGENTS_STATUS -eq 200 ]; then
    print_status "Agents list endpoint passed (HTTP 200)"
else
    print_error "Agents list endpoint failed (HTTP $AGENTS_STATUS)"
fi

echo ""
echo "📊 Deployment Summary"
echo "--------------------"
echo "Cloud Function URL: $FUNCTION_URL"
echo "API Gateway URL: $SERVICE_URL"
echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "Next steps:"
echo "1. Update frontend .env.production with: REACT_APP_AGENT_API_URL=$SERVICE_URL"
echo "2. Deploy frontend to Vercel/Netlify"
echo "3. Run compliance tests: ./test-compliance.sh"
echo ""
echo "⚠️ IMPORTANT: Update JWT_SECRET in production!"
echo "Current JWT_SECRET is using default value - change it for production!"
