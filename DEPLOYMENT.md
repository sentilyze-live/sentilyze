# Sentilyze Deployment Guide

This guide covers deploying the Sentilyze platform to Google Cloud Platform (GCP) for production use.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Service Deployment](#service-deployment)
5. [Post-Deployment](#post-deployment)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

- **Google Cloud SDK** (`gcloud`) - [Installation Guide](https://cloud.google.com/sdk/docs/install)
- **Terraform** >= 1.5.0 - [Installation Guide](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- **Docker** - [Installation Guide](https://docs.docker.com/get-docker/)
- **Git** - [Installation Guide](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

### Required GCP Permissions

Your GCP account needs the following roles:

- `roles/owner` on the project (or equivalent combination of roles)
- `roles/storage.admin` - For GCS buckets
- `roles/pubsub.admin` - For Pub/Sub topics
- `roles/bigquery.admin` - For BigQuery datasets
- `roles/run.admin` - For Cloud Run
- `roles/cloudsql.admin` - For Cloud SQL
- `roles/redis.admin` - For Memorystore
- `roles/secretmanager.admin` - For Secret Manager
- `roles/cloudbuild.builds.editor` - For Cloud Build
- `roles/monitoring.admin` - For Cloud Monitoring

### GCP Project Structure

We recommend three separate projects:

```
sentilyze-v5-clean     - Production environment
sentilyze-dev          - Development environment
sentilyze-staging      - Staging/QA environment
```

**Note:** For this deployment, we use `sentilyze-v5-clean` as the primary project ID.

---

## Initial Setup

### 1. Create GCP Projects

```bash
# Production (primary project)
gcloud projects create sentilyze-v5-clean --name="Sentilyze v5 Clean"

# Development
gcloud projects create sentilyze-dev --name="Sentilyze Development"

# Staging  
gcloud projects create sentilyze-staging --name="Sentilyze Staging"
```

### 2. Enable Billing

Enable billing for each project:
```bash
gcloud billing projects link sentilyze-v5-clean --billing-account=YOUR_BILLING_ACCOUNT
gcloud billing projects link sentilyze-dev --billing-account=YOUR_BILLING_ACCOUNT
gcloud billing projects link sentilyze-staging --billing-account=YOUR_BILLING_ACCOUNT
```

### 3. Configure gcloud

```bash
# Set default project (use the appropriate one)
gcloud config set project sentilyze-v5-clean

# Set default region
gcloud config set compute/region us-central1

# Authenticate
gcloud auth login
gcloud auth application-default login
```

### 4. Create Terraform State Bucket

```bash
# Create bucket for Terraform state (do this for each project)
gcloud storage buckets create gs://sentilyze-terraform-state \
  --project=sentilyze-v5-clean \
  --location=us-central1 \
  --uniform-bucket-level-access

# Enable versioning
gcloud storage buckets update gs://sentilyze-terraform-state --versioning
```

### 5. Configure Artifact Registry

```bash
# Create Docker repository
gcloud artifacts repositories create sentilyze \
  --repository-format=docker \
  --location=us-central1 \
  --description="Sentilyze container images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## Infrastructure Deployment

### 1. Prepare Terraform Variables

Create a `terraform.tfvars` file for each environment:

**Production (`infrastructure/terraform/production.tfvars`):**
```hcl
gcp_project_id = "sentilyze-v5-clean"
gcp_region     = "us-central1"
environment    = "production"

# Feature flags
enable_crypto_market     = true
enable_gold_market       = true
enable_crypto_predictions = true
enable_gold_predictions   = true

# Infrastructure
enable_redis    = true
enable_postgres = true
redis_tier      = "STANDARD_HA"
redis_memory_size = 8

# Scaling
min_instances = 2
max_instances = 100

# Alerts
alert_email_addresses = ["ops@yourdomain.com", "devops@yourdomain.com"]

# GitHub (for Cloud Build triggers)
github_owner = "your-github-org"
github_repo  = "sentilyze"
```

### 2. Initialize Terraform

```bash
cd infrastructure/terraform

# Initialize (first time only)
terraform init

# Or reconfigure for different backend
terraform init -reconfigure \
  -backend-config="bucket=sentilyze-terraform-state" \
  -backend-config="prefix=terraform/state"
```

### 3. Plan Infrastructure

```bash
# Review changes
cd infrastructure/terraform
terraform plan -var-file=production.tfvars
```

### 4. Apply Infrastructure

```bash
# Deploy infrastructure (takes ~15-20 minutes)
terraform apply -var-file=production.tfvars

# Save outputs
terraform output -json > terraform-outputs.json
```

**Infrastructure Created:**
- Service accounts for each service
- Pub/Sub topics and subscriptions
- BigQuery dataset with tables and views
- Cloud Storage buckets
- Memorystore Redis instance
- Cloud SQL PostgreSQL instance
- Secret Manager secrets (empty - you'll populate these)
- Cloud Run services (with placeholder images)
- Cloud Build triggers
- Cloud Scheduler jobs
- Monitoring alerts

### 5. Configure Secrets

Populate required secrets in Secret Manager:

```bash
# Database password
echo -n "your-secure-db-password" | gcloud secrets create db-password \
  --data-file=- --project=sentilyze-v5-clean

# API Keys
echo -n "your-coinmarketcap-key" | gcloud secrets create coinmarketcap-api-key \
  --data-file=- --project=sentilyze-v5-clean

echo -n "your-gold-api-key" | gcloud secrets create gold-api-key \
  --data-file=- --project=sentilyze-v5-clean

echo -n "your-twitter-bearer-token" | gcloud secrets create twitter-bearer-token \
  --data-file=- --project=sentilyze-v5-clean

echo -n "your-reddit-client-id" | gcloud secrets create reddit-client-id \
  --data-file=- --project=sentilyze-v5-clean

echo -n "your-reddit-client-secret" | gcloud secrets create reddit-client-secret \
  --data-file=- --project=sentilyze-v5-clean

echo -n "your-huggingface-api-key" | gcloud secrets create huggingface-api-key \
  --data-file=- --project=sentilyze-v5-clean

# Email/SMTP
echo -n "your-smtp-password" | gcloud secrets create smtp-password \
  --data-file=- --project=sentilyze-v5-clean

# Slack/Discord webhooks (optional)
echo -n "your-slack-webhook-url" | gcloud secrets create slack-webhook-url \
  --data-file=- --project=sentilyze-v5-clean

echo -n "your-discord-webhook-url" | gcloud secrets create discord-webhook-url \
  --data-file=- --project=sentilyze-v5-clean
```

---

## Service Deployment

### Option 1: Cloud Build (Recommended)

Deploy all services using Cloud Build:

```bash
# Submit build (deploys all services)
gcloud builds submit \
  --config infrastructure/cloudbuild/cloudbuild.yaml \
  --project=sentilyze-v5-clean
```

**What happens:**
1. Builds Docker images for all 8 services
2. Pushes to Artifact Registry
3. Deploys to Cloud Run (no traffic initially)
4. Migrates traffic to new revisions

**Web frontend (Next.js):** deploy separately after the backend, for example:

```bash
# Linux/macOS (bash)
./scripts/deploy-web.sh gcp --project-id=sentilyze-v5-clean --env-file=apps/web/.env.production
```

```powershell
# Windows (PowerShell)
.\scripts\deploy-web.ps1 -ProjectId sentilyze-v5-clean -EnvFile apps\web\.env.production
```

### Option 2: Manual Deployment

Deploy individual services:

```bash
# Build and push a single service
cd services/api-gateway
docker build -t us-central1-docker.pkg.dev/sentilyze-v5-clean/sentilyze/api-gateway:latest .
docker push us-central1-docker.pkg.dev/sentilyze-v5-clean/sentilyze/api-gateway:latest

# Deploy to Cloud Run
gcloud run deploy api-gateway \
  --image=us-central1-docker.pkg.dev/sentilyze-v5-clean/sentilyze/api-gateway:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=sentilyze-api-gateway@sentilyze-v5-clean.iam.gserviceaccount.com \
  --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=sentilyze-v5-clean"
```

### Option 3: Using Makefile

```bash
# Deploy to production
make deploy-production

# Or with explicit project
make deploy GCP_PROJECT_ID=sentilyze-v5-clean
```

---

## Post-Deployment

### 1. Verify Services

Check that all services are running:

```bash
# List all services
gcloud run services list --project=sentilyze-v5-clean

# Check specific service
gcloud run services describe api-gateway --region=us-central1

# Test API Gateway
curl https://api-gateway-xxx-uc.a.run.app/health
```

### 2. Initialize Database

Connect to PostgreSQL and run migrations:

```bash
# Get connection name
export DB_CONNECTION=$(gcloud sql instances describe sentilyze-postgres \
  --format='value(connectionName)' --project=sentilyze-v5-clean)

# Connect using Cloud SQL Proxy (in separate terminal)
cloud-sql-proxy --port 5432 $DB_CONNECTION

# Run migrations (using your migration tool or psql)
psql -h localhost -U sentilyze -d sentilyze_predictions \
  -f infrastructure/postgres/migrations/001_initial_schema.sql
```

### 3. Test Pub/Sub

Publish a test message:

```bash
# Publish test message
gcloud pubsub topics publish raw-market-data \
  --message='{"test": "data"}' \
  --project=sentilyze-v5-clean

# Check subscription
gcloud pubsub subscriptions pull raw-data-subscription \
  --auto-ack --project=sentilyze-v5-clean
```

### 4. Configure Cloud Scheduler

Verify scheduled jobs are running:

```bash
# List jobs
gcloud scheduler jobs list --project=sentilyze-v5-clean

# Test a job
gcloud scheduler jobs run crypto-data-ingestion \
  --project=sentilyze-v5-clean
```

---

## Monitoring & Maintenance

### 1. Set Up Monitoring Dashboards

```bash
# Create monitoring dashboard
gcloud monitoring dashboards create \
  --config-from-file=infrastructure/monitoring/dashboard.json \
  --project=sentilyze-v5-clean
```

### 2. Configure Alerting

Add notification channels:

```bash
# Create email notification channel
gcloud monitoring channels create \
  --channel-labels=email_address=alerts@yourdomain.com \
  --display-name="Sentilyze Alerts" \
  --type=email \
  --project=sentilyze-v5-clean
```

### 3. View Logs

```bash
# All services
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=50 --project=sentilyze-v5-clean

# Specific service
gcloud logging read "resource.labels.service_name=api-gateway" \
  --limit=50 --project=sentilyze-v5-clean

# Errors only
gcloud logging read "severity>=ERROR" \
  --limit=50 --project=sentilyze-v5-clean
```

### 4. Performance Monitoring

Check service metrics:

```bash
# CPU/Memory utilization
gcloud monitoring metrics list \
  --filter="metric.type:run.googleapis.com/container" \
  --project=sentilyze-v5-clean

# Request latency
gcloud monitoring metrics list \
  --filter="metric.type:run.googleapis.com/request_latencies" \
  --project=sentilyze-v5-clean
```

---

## Troubleshooting

### Common Issues

#### 1. Services Not Starting

```bash
# Check service logs
gcloud logging read "resource.labels.service_name=api-gateway AND severity>=ERROR" \
  --limit=20 --project=sentilyze-v5-clean --format="table(timestamp, textPayload)"

# Check service configuration
gcloud run services describe api-gateway --region=us-central1 --project=sentilyze-v5-clean
```

#### 2. Database Connection Issues

```bash
# Test connectivity
gcloud sql connect sentilyze-postgres \
  --user=sentilyze \
  --database=sentilyze_predictions \
  --project=sentilyze-v5-clean

# Check Cloud SQL Proxy logs
# Ensure service account has Cloud SQL Client role
gcloud projects add-iam-policy-binding sentilyze-v5-clean \
  --member="serviceAccount:sentilyze-prediction-engine@sentilyze-v5-clean.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

#### 3. Pub/Sub Message Backlog

```bash
# Check subscription backlog
gcloud pubsub subscriptions list --project=sentilyze-v5-clean

# Check ack latency
gcloud monitoring metrics list \
  --filter="metric.type:pubsub.googleapis.com/subscription/ack_latencies" \
  --project=sentilyze-v5-clean

# Scale up sentiment processor if needed
gcloud run services update sentiment-processor \
  --max-instances=200 --region=us-central1 --project=sentilyze-v5-clean
```

#### 4. BigQuery Query Performance

```bash
# Check slot usage
gcloud monitoring metrics list \
  --filter="metric.type:bigquery.googleapis.com/slots/allocated_for_project" \
  --project=sentilyze-v5-clean

# Optimize queries in views/
# Consider materialized views for expensive queries
```

#### 5. Redis Connection Issues

```bash
# Check Redis status
gcloud redis instances describe sentilyze-cache \
  --region=us-central1 --project=sentilyze-v5-clean

# Test connectivity from service
# (SSH into service or use Cloud Run exec)
```

### Debug Mode

Enable debug logging:

```bash
# Update service with debug logging
gcloud run services update api-gateway \
  --set-env-vars="LOG_LEVEL=DEBUG" \
  --region=us-central1 \
  --project=sentilyze-v5-clean
```

---

## Rollback Procedures

### Rollback Service Deployment

```bash
# Rollback to previous revision
gcloud run services update-traffic api-gateway \
  --to-revisions=PREVIOUS=100 \
  --region=us-central1 \
  --project=sentilyze-v5-clean

# Or specific revision
gcloud run services update-traffic api-gateway \
  --to-revisions=api-gateway-00001-abc=100 \
  --region=us-central1 \
  --project=sentilyze-v5-clean
```

### Rollback Infrastructure

```bash
# View previous states
terraform state list
terraform state pull > backup.tfstate

# Rollback to previous version
terraform apply -var-file=production.tfvars \
  -target=google_cloud_run_v2_service.api-gateway

# Or destroy and recreate specific resource
terraform destroy -var-file=production.tfvars \
  -target=google_cloud_run_v2_service.api-gateway
terraform apply -var-file=production.tfvars \
  -target=google_cloud_run_v2_service.api-gateway
```

### Emergency Stop

Disable all ingestion:

```bash
# Pause Cloud Scheduler jobs
gcloud scheduler jobs pause crypto-data-ingestion --project=sentilyze-v5-clean
gcloud scheduler jobs pause gold-data-ingestion --project=sentilyze-v5-clean

# Scale down ingestion service
gcloud run services update ingestion \
  --min-instances=0 --max-instances=0 \
  --region=us-central1 --project=sentilyze-v5-clean
```

---

## Cost Optimization

### 1. Right-Size Resources

```bash
# Check actual usage
gcloud monitoring metrics list \
  --filter="metric.type:run.googleapis.com/container/memory/utilizations" \
  --project=sentilyze-v5-clean

# Adjust memory/CPU based on usage
gcloud run services update api-gateway \
  --memory=512Mi --cpu=1 \
  --region=us-central1 --project=sentilyze-v5-clean
```

### 2. Use Preemptible Resources (Non-Prod)

For staging/development:

```hcl
# In terraform.tfvars for staging
redis_tier = "BASIC"
min_instances = 0
```

### 3. BigQuery Cost Control

```sql
-- Set table expiration (in BigQuery)
ALTER TABLE `sentilyze_dataset.raw_data`
SET OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 90 DAY));
```

---

## Security Hardening

### 1. VPC Configuration

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create sentilyze-connector \
  --network=default \
  --region=us-central1 \
  --range=10.8.0.0/28 \
  --project=sentilyze-v5-clean

# Update service to use VPC
gcloud run services update api-gateway \
  --vpc-connector=sentilyze-connector \
  --region=us-central1 \
  --project=sentilyze-v5-clean
```

### 2. Enable Cloud Armor

```bash
# Create security policy
gcloud compute security-policies create sentilyze-policy \
  --description="Sentilyze security policy"

# Add rules (DDoS, SQL injection, etc.)
gcloud compute security-policies rules create 1000 \
  --security-policy=sentilyze-policy \
  --expression="true" \
  --action="allow"
```

### 3. Rotate Secrets

```bash
# Rotate API key
gcloud secrets versions add coinmarketcap-api-key \
  --data-file=- <<< "new-api-key"

# Disable old version
gcloud secrets versions disable 1 --secret=coinmarketcap-api-key
```

---

## Production Checklist

Before going live:

- [ ] All secrets configured in Secret Manager
- [ ] Database migrations applied
- [ ] BigQuery tables created and partitioned
- [ ] Cloud Run services deployed and healthy
- [ ] Pub/Sub topics and subscriptions verified
- [ ] Cloud Scheduler jobs active
- [ ] Monitoring dashboards created
- [ ] Alert policies configured
- [ ] Load testing completed
- [ ] Disaster recovery plan documented
- [ ] Runbook created for on-call
- [ ] SSL certificates configured (automatic with Cloud Run)
- [ ] Custom domain configured (optional)
- [ ] Backup policies configured

---

## Support

For deployment issues:

1. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Review service logs: `gcloud logging read`
3. Check Terraform state: `terraform show`
4. Contact: devops@yourdomain.com

---

**Deployment completed!** 🚀

Your Sentilyze platform is now running on GCP. Monitor the dashboard and review predictions as data flows through the system.
