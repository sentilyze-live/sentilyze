#!/bin/bash
# Deploy script for ML Services (Semantic Cache + Knowledge Graph)
# 
# Usage:
#   ./deploy-ml-services.sh <project_id>
#
# Example:
#   ./deploy-ml-services.sh sentilyze-v5-clean

set -e

PROJECT_ID=${1:-sentilyze-v5-clean}
REGION=${2:-us-central1}
CACHE_BUCKET="${PROJECT_ID}-cache"
echo "🚀 Deploying ML Services for project: ${PROJECT_ID}"
echo "📍 Region: ${REGION}"
echo ""

# Step 1: Create Cloud Storage bucket for FAISS index persistence
echo "📦 Step 1: Creating Cloud Storage bucket..."
if ! gsutil ls -b "gs://${CACHE_BUCKET}" 2>/dev/null; then
    gsutil mb -p "${PROJECT_ID}" -l "${REGION}" -c STANDARD "gs://${CACHE_BUCKET}"
    echo "✅ Bucket created: gs://${CACHE_BUCKET}"
else
    echo "✅ Bucket already exists: gs://${CACHE_BUCKET}"
fi

# Step 2: Set bucket lifecycle policy
echo "🗑️  Step 2: Setting bucket lifecycle policy..."
cat > /tmp/lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "numNewerVersions": 3
        }
      },
      {
        "action": {
          "type": "SetStorageClass",
          "storageClass": "NEARLINE"
        },
        "condition": {
          "age": 7,
          "matchesPrefix": ["semantic_cache/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json "gs://${CACHE_BUCKET}"
echo "✅ Lifecycle policy set"

# Step 3: Set bucket IAM policy
echo "🔐 Step 3: Setting bucket IAM policies..."
# Allow sentiment-processor service account to read/write
gcloud storage buckets add-iam-policy-binding "gs://${CACHE_BUCKET}" \
    --member="serviceAccount:sentilyze-sa-sentiment-processor@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --condition=None

# Allow application default credentials
gcloud storage buckets add-iam-policy-binding "gs://${CACHE_BUCKET}" \
    --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
    --role="roles/storage.objectViewer" \
    --condition=None

echo "✅ IAM policies set"

# Step 4: Create Firestore indexes
echo "📊 Step 4: Creating Firestore indexes..."
gcloud firestore indexes create infrastructure/firestore-indexes.json --project="${PROJECT_ID}" || {
    echo "⚠️  Some indexes may already exist or are being created"
}
echo "✅ Firestore indexes submitted (creation may take 5-10 minutes)"

# Step 5: Enable required APIs
echo "🔌 Step 5: Enabling required APIs..."
gcloud services enable aiplatform.googleapis.com --project="${PROJECT_ID}"
gcloud services enable firestore.googleapis.com --project="${PROJECT_ID}"
echo "✅ APIs enabled"

# Step 6: Build and push Docker image
echo "🐳 Step 6: Building Docker image..."
cd services/sentiment-processor

# Download spaCy model for embedding
echo "📥 Downloading spaCy model..."
pip install spacy
python -m spacy download en_core_web_sm

# Build with Cloud Build
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/sentiment-processor:latest" \
    --project="${PROJECT_ID}"

cd ../..
echo "✅ Docker image built and pushed"

# Step 7: Deploy to Cloud Run
echo "☁️  Step 7: Deploying to Cloud Run..."
# Substitute variables in service.yaml
export GCP_PROJECT_ID="${PROJECT_ID}"
envsubst < infrastructure/cloudrun/sentiment-processor.yaml > /tmp/sentiment-processor-deploy.yaml

# Deploy
gcloud run services replace /tmp/sentiment-processor-deploy.yaml \
    --project="${PROJECT_ID}" \
    --region="${REGION}"

echo "✅ Cloud Run service deployed"

# Step 8: Get service URL
echo "🔗 Step 8: Getting service URL..."
SERVICE_URL=$(gcloud run services describe sentiment-processor \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)')

echo "✅ Service URL: ${SERVICE_URL}"

# Step 9: Health check
echo "🏥 Step 9: Running health check..."
sleep 10  # Wait for service to be ready

curl -f "${SERVICE_URL}/health/ready" || {
    echo "⚠️  Health check failed, but deployment is complete"
}

echo ""
echo "✅🎉 ML Services deployment complete!"
echo ""
echo "📋 Summary:"
echo "   - Cloud Storage Bucket: gs://${CACHE_BUCKET}"
echo "   - Cloud Run Service: ${SERVICE_URL}"
echo "   - Firestore Collections: semantic_cache, knowledge_graph"
echo ""
echo "🔍 Verification Commands:"
echo "   # Check service logs:"
echo "   gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=sentiment-processor' --limit=50 --project=${PROJECT_ID}"
echo ""
echo "   # Test semantic cache:"
echo "   curl -X POST ${SERVICE_URL}/api/v1/analyze -H 'Content-Type: application/json' -d '{\"text\":\"Gold prices soaring today\"}'"
echo ""
echo "   # Check cache stats:"
echo "   curl ${SERVICE_URL}/api/v1/cache/stats"
echo ""
echo "💡 Next Steps:"
echo "   1. Monitor cache hit rates in logs"
echo "   2. Verify Knowledge Graph is building from processed texts"
echo "   3. Check Cloud Storage for FAISS index backups"
echo "   4. Monitor Firestore read/write costs"
