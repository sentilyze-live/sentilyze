#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEPLOY_TARGET="${1:-local}"
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
ENV_FILE="${WEB_ENV_FILE:-}"

# Help message
show_help() {
    echo "Usage: ./deploy-web.sh [TARGET] [OPTIONS]"
    echo ""
    echo "Targets:"
    echo "  local       Build and run locally with Docker"
    echo "  vercel      Deploy to Vercel"
    echo "  gcp         Deploy to Google Cloud Run"
    echo "  docker      Build Docker image only"
    echo ""
    echo "Options:"
    echo "  --project-id    GCP Project ID (for gcp target)"
    echo "  --region        GCP Region (default: us-central1)"
    echo "  --env-file      Path to .env file to load (for gcp target)"
    echo ""
    echo "Examples:"
    echo "  ./deploy-web.sh local"
    echo "  ./deploy-web.sh vercel"
    echo "  ./deploy-web.sh gcp --project-id=my-project"
    echo "  ./deploy-web.sh gcp --project-id=my-project --env-file=.env.production"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            DEPLOY_TARGET="$1"
            shift
            ;;
    esac
done

echo -e "${BLUE}🚀 Deploying Sentilyze Web...${NC}"
echo -e "${BLUE}Target: ${DEPLOY_TARGET}${NC}"

# Change to web app directory
cd apps/web

case $DEPLOY_TARGET in
    local)
        echo -e "${YELLOW}📦 Building for local development...${NC}"
        npm install
        npm run build
        echo -e "${GREEN}✅ Build complete! Starting development server...${NC}"
        npm run start
        ;;

    docker)
        echo -e "${YELLOW}🐳 Building Docker image...${NC}"
        docker build -t sentilyze-web:latest .
        echo -e "${GREEN}✅ Docker image built: sentilyze-web:latest${NC}"
        echo -e "${YELLOW}To run: docker run -p 3000:3000 sentilyze-web:latest${NC}"
        ;;

    vercel)
        echo -e "${YELLOW}▲ Deploying to Vercel...${NC}"
        
        # Check if Vercel CLI is installed
        if ! command -v vercel &> /dev/null; then
            echo -e "${YELLOW}Installing Vercel CLI...${NC}"
            npm install -g vercel
        fi
        
        # Check if logged in
        if ! vercel whoami &> /dev/null; then
            echo -e "${YELLOW}Please login to Vercel first:${NC}"
            vercel login
        fi
        
        # Deploy
        echo -e "${YELLOW}Deploying to Vercel...${NC}"
        vercel --prod
        
        echo -e "${GREEN}✅ Deployed to Vercel!${NC}"
        ;;

    gcp)
        echo -e "${YELLOW}☁️  Deploying to Google Cloud Run...${NC}"
        
        # Check if gcloud is installed
        if ! command -v gcloud &> /dev/null; then
            echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
            exit 1
        fi
        
        # Check project ID
        if [ -z "$PROJECT_ID" ]; then
            PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
            if [ -z "$PROJECT_ID" ]; then
                echo -e "${RED}❌ No GCP project ID specified. Use --project-id or set GCP_PROJECT_ID env var.${NC}"
                exit 1
            fi
        fi
        
        echo -e "${BLUE}Using project: ${PROJECT_ID}${NC}"
        echo -e "${BLUE}Using region: ${REGION}${NC}"
        
        IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/sentilyze/web:latest"

        # Build and push container image
        echo -e "${YELLOW}Building container image...${NC}"
        gcloud builds submit --tag "${IMAGE_URI}" --project "${PROJECT_ID}"
        
        # Deploy to Cloud Run
        echo -e "${YELLOW}Deploying to Cloud Run...${NC}"

        # Build env vars argument
        ENV_VARS="NODE_ENV=production"
        if [ -n "${ENV_FILE}" ] && [ -f "${ENV_FILE}" ]; then
            echo -e "${BLUE}Loading env vars from: ${ENV_FILE}${NC}"
            while IFS= read -r line || [ -n "$line" ]; do
                # Trim whitespace
                line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
                # Skip empty lines and comments
                if [ -z "$line" ] || [[ "$line" == \#* ]]; then
                    continue
                fi
                # Skip invalid lines (no equals sign)
                if [[ "$line" != *"="* ]]; then
                    continue
                fi
                ENV_VARS="${ENV_VARS},${line}"
            done < "${ENV_FILE}"
        elif [ -n "${ENV_FILE}" ]; then
            echo -e "${YELLOW}⚠️  Env file not found: ${ENV_FILE} (continuing with NODE_ENV only)${NC}"
        fi

        gcloud run deploy sentilyze-web \
            --image "${IMAGE_URI}" \
            --platform managed \
            --region ${REGION} \
            --project ${PROJECT_ID} \
            --allow-unauthenticated \
            --port 3000 \
            --set-env-vars="${ENV_VARS}" \
            --memory=1Gi \
            --cpu=1 \
            --concurrency=80 \
            --max-instances=10
        
        # Get the service URL
        SERVICE_URL=$(gcloud run services describe sentilyze-web \
            --region ${REGION} \
            --project ${PROJECT_ID} \
            --format 'value(status.url)')
        
        echo -e "${GREEN}✅ Deployed to Cloud Run!${NC}"
        echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
        ;;

    *)
        echo -e "${RED}❌ Unknown target: ${DEPLOY_TARGET}${NC}"
        show_help
        exit 1
        ;;
esac

echo -e "${GREEN}✅ Deployment complete!${NC}"
