# Google Cloud Platform Usage Documentation
## Sentilyze Project - Google for Startups Cloud Program Application

---

## 📋 Executive Summary

**Sentilyze** is a **fully cloud-native** financial technology platform developed using nearly all core services of Google Cloud Platform. The project maximizes the power and flexibility of Google's modern cloud architecture.

### Project Characteristics
- **Development Process**: Built by one person with AI assistance, with zero coding knowledge
- **Architecture**: Event-driven microservices architecture
- **Number of Services**: 8 independent microservices
- **Technology**: Python, FastAPI, Next.js, TypeScript
- **Deployment**: Fully automated CI/CD

---

## 🌟 Why Google Cloud Platform?

### Strategic Selection Reasons

1. **AI Integration**: Vertex AI and Google's AI services
2. **Serverless Architecture**: Cost optimization with Cloud Run
3. **Event-Driven**: Scalable messaging with Pub/Sub
4. **Data Analytics**: Petabyte-scale analysis capacity with BigQuery
5. **Security**: Enterprise-grade security standards
6. **Flexibility**: Infrastructure as Code (Terraform) support

---

## ☁️ Google Cloud Services Used

### 1. Cloud Run ⭐⭐⭐⭐⭐

**Usage**: Hosting all 8 microservices

**Why Chosen**:
- Serverless: No charge when not in use (scale-to-zero)
- Auto-scaling: From 0 to 100+ instances
- Container-based: Development in any language
- Pay-per-use: Charged only during processing

**Our Services**:

| Service | Traffic | Scaling | Estimated Monthly Cost |
|---------|---------|---------|----------------------|
| **API Gateway** | High | 1-50 instances | $50-150 |
| **Ingestion** | Medium | 0-20 instances | $30-80 |
| **Sentiment Processor** | High | 0-100 instances | $100-300 |
| **Market Context** | Medium | 0-50 instances | $50-150 |
| **Prediction Engine** | Medium | 0-50 instances | $50-150 |
| **Alert Service** | Low | 0-20 instances | $20-50 |
| **Tracker Service** | Low | 0-10 instances | $10-30 |
| **Analytics Engine** | Low | 0-10 instances | $20-60 |

**Total Cloud Run Cost**: ~$330-970/month

**Why Important**: Provides 60-70% cost savings compared to traditional VMs. Scale-to-zero feature keeps costs minimal during low traffic periods.

---

### 2. Cloud Pub/Sub ⭐⭐⭐⭐⭐

**Usage**: Event-driven communication between services

**Pub/Sub Topics**: 7 topics
- `raw-events`: Raw data stream
- `processed-sentiment`: Processed sentiment data
- `market-context`: Technical analysis data
- `processed-events`: Processed events
- `predictions`: Forecasts
- `alerts`: Notifications
- `analytics-events`: Analytics events

**Push Subscriptions**: 8 (Cloud Run compatible)
**Pull Subscriptions**: 4 (For batch processing)

**Message Volume**:
- Daily: ~100,000-500,000 messages
- Monthly: ~3-15 million messages

**Estimated Monthly Cost**: $20-100

**Why Important**: 
- Enables independent scaling by separating services
- Message guarantee and retry mechanism
- Supports both real-time and batch processing

---

### 3. BigQuery ⭐⭐⭐⭐⭐

**Usage**: Data warehouse, analytics, and ML feature store

**Dataset**: `sentilyze_dataset`

**Tables** (7 tables):
1. **raw_data**: Raw market data (~1M rows/month)
2. **sentiment_analysis**: Sentiment scores (~500K rows/month)
3. **market_context**: Technical indicators (~200K rows/month)
4. **predictions**: Forecasts (~50K rows/month)
5. **prediction_accuracy**: Accuracy metrics (~10K rows/month)
6. **alerts**: Notification history (~5K rows/month)
7. **analytics_summary**: Daily summaries (~30 rows/day)

**Views** (4 views):
- `daily_sentiment_summary`: Daily sentiment summary
- `prediction_performance`: Model performance analysis
- `crypto_market_overview`: Crypto market overview
- `gold_market_overview`: Gold market overview

**Features**:
- **Partitioning**: Daily partitions (timestamp field)
- **Clustering**: market_type, asset_symbol
- **Retention**: 90 days (raw), 1 year (processed)

**Data Volume**:
- Storage: ~50-200 GB
- Monthly queries: ~10-50 TB processed

**Estimated Monthly Cost**: $50-200

**Why Important**:
- Petabyte-scale query capacity
- Easy analysis with SQL
- Feature store for ML model training
- Real-time streaming insert support

---

### 4. Cloud SQL (PostgreSQL) ⭐⭐⭐⭐

**Usage**: Relational data - Prediction tracking and user management

**Instance**: 
- Development: db-f1-micro (0.6 GB RAM)
- Production: db-n1-standard-2 (7.5 GB RAM)

**Databases**:
- `sentilyze_predictions`: Prediction tracking
- `admin_panel`: User and feature management

**Features**:
- Automatic backups (daily)
- High availability (production)
- Private IP (VPC integration)
- Point-in-time recovery

**Data Volume**:
- Row count: ~100K predictions
- Storage: ~5-20 GB

**Estimated Monthly Cost**: $50-200

**Why Important**:
- ACID-compliant transactions
- Complex query support
- Foreign key constraints
- Managed service (no maintenance)

---

### 5. Firestore ⭐⭐⭐⭐

**Usage**: NoSQL cache, session storage, feature flags

**Collections**:
- `cache`: API response cache (5 min TTL)
- `sessions`: User sessions
- `feature_flags`: Feature flags
- `rate_limits`: Rate limiting counters

**Features**:
- Real-time updates
- Offline support
- Automatic scaling
- Strong consistency

**Data Volume**:
- Document count: ~10K-50K
- Reads: ~1-5M/month
- Writes: ~500K-2M/month

**Estimated Monthly Cost**: $20-80

**Why Important**:
- Redis alternative (Google-native)
- Compatible with scale-to-zero Cloud Run
- Real-time capabilities
- Lower latency (same-region)

---

### 6. Secret Manager ⭐⭐⭐⭐⭐

**Usage**: API keys, credentials, sensitive information

**Secrets** (17 secrets):
- Database credentials
- Crypto API keys (5)
- Gold API keys (4)
- Social media API keys (2)
- ML/AI API keys (2)
- Notification credentials (4)

**Features**:
- Automatic versioning
- IAM integration
- Audit logging
- Encryption at rest

**Estimated Monthly Cost**: $5-15

**Why Important**:
- Secure credential management
- Environment variable injection
- Easy rotation
- Compliance requirements

---

### 7. Cloud Build ⭐⭐⭐⭐⭐

**Usage**: CI/CD pipeline - Automated build and deploy

**Triggers**: 8 (one for each service)

**Build Pipeline**:
1. Source checkout (GitHub)
2. Docker image build (multi-stage)
3. Image push to Artifact Registry
4. Deploy to Cloud Run
5. Health check
6. Traffic migration

**Build Frequency**:
- Development: ~5-10 builds/day
- Production: ~1-3 builds/day

**Features**:
- Parallel builds
- Build caching
- Custom build steps
- Approval gates (production)

**Estimated Monthly Cost**: $20-80

**Why Important**:
- Fully automated deployment
- Zero-downtime releases
- Built-in testing integration
- Native GCP integration

---

### 8. Artifact Registry ⭐⭐⭐⭐

**Usage**: Docker image registry

**Repositories**:
- `sentilyze-repo`: All service images

**Images** (8 services x 2-3 versions):
- ~16-24 active images
- Image size: 200-500 MB/image
- Total storage: ~5-10 GB

**Features**:
- Vulnerability scanning
- Access control (IAM)
- Geo-replication
- Automatic cleanup policies

**Estimated Monthly Cost**: $5-20

**Why Important**:
- Native integration with Cloud Run
- Security scanning
- Fast image pull
- Version management

---

### 9. Cloud Storage ⭐⭐⭐⭐

**Usage**: Object storage - ML models, backups, logs

**Buckets**:
1. **sentilyze-v5-clean-sentilyze**: General data
2. **sentilyze-v5-clean-sentilyze-models**: ML models
3. **sentilyze-v5-clean-terraform-state**: Terraform state

**Features**:
- Versioning enabled
- Lifecycle rules (90-day retention)
- Regional storage
- Automatic backups

**Storage Volume**: ~20-50 GB

**Estimated Monthly Cost**: $5-15

**Why Important**:
- ML model versioning
- Infrastructure state management
- Log archiving
- 99.99% durability

---

### 10. Cloud Scheduler ⭐⭐⭐⭐

**Usage**: Scheduled tasks

**Jobs** (2 jobs):
1. **crypto-data-ingestion**: Every 5 minutes
2. **gold-data-ingestion**: Every 15 minutes

**Features**:
- Cron syntax
- Timezone support
- OAuth authentication
- Retry policies

**Monthly Executions**:
- Crypto: ~8,640 invocations/month
- Gold: ~2,880 invocations/month

**Estimated Monthly Cost**: $5-10

**Why Important**:
- Reliable scheduling
- Cloud Run integration
- Automatic retries
- Cost-effective

---

### 11. Cloud Logging ⭐⭐⭐⭐⭐

**Usage**: Centralized log management

**Log Sources**:
- Cloud Run (8 services)
- Cloud Build
- Cloud Scheduler
- Application logs (structlog)

**Log Volume**: ~5-20 GB/month

**Features**:
- Structured logging
- Log-based metrics
- Log analysis
- Export to BigQuery

**Estimated Monthly Cost**: $10-40

**Why Important**:
- Debugging
- Audit trails
- Security monitoring
- Performance analysis

---

### 12. Cloud Monitoring ⭐⭐⭐⭐⭐

**Usage**: Metrics, dashboards, alerts

**Monitored Metrics**:
- Request rate, latency, errors (Cloud Run)
- CPU, memory utilization
- Pub/Sub message lag
- Database connections
- Custom business metrics

**Alert Policies** (5 policies):
- High error rate (>5%)
- High latency (>2s p95)
- Service down (>5 min)
- Pub/Sub backlog (>10K)
- Database connection pool exhausted

**Notification Channels**:
- Email
- Slack (planned)

**Estimated Monthly Cost**: $10-30

**Why Important**:
- Proactive issue detection
- Performance optimization
- SLA monitoring
- Cost tracking

---

### 13. Cloud Trace ⭐⭐⭐

**Usage**: Distributed tracing

**Features**:
- Request tracing across services
- Latency analysis
- Service dependency mapping
- Performance bottleneck detection

**Estimated Monthly Cost**: $5-15

**Why Important**:
- Performance debugging
- Service optimization
- User experience improvement

---

### 14. Vertex AI ⭐⭐⭐⭐

**Usage**: AI/ML model hosting and inference

**Models**:
- Hugging Face transformers
- Custom sentiment models
- OpenAI API proxy

**Features**:
- Model versioning
- A/B testing capability
- Automatic scaling
- Batch prediction

**Estimated Monthly Cost**: $50-200 (planned)

**Why Important**:
- Managed ML infrastructure
- GPU acceleration
- Model monitoring
- Easy deployment

---

## 💰 Total Cost Analysis

### Estimated Monthly Costs

| Service | Development | Production |
|--------|-------------|------------|
| Cloud Run | $100-200 | $330-970 |
| Pub/Sub | $10-30 | $20-100 |
| BigQuery | $20-50 | $50-200 |
| Cloud SQL | $25-50 | $50-200 |
| Firestore | $10-30 | $20-80 |
| Secret Manager | $5-10 | $5-15 |
| Cloud Build | $10-30 | $20-80 |
| Artifact Registry | $5-10 | $5-20 |
| Cloud Storage | $5-10 | $5-15 |
| Cloud Scheduler | $2-5 | $5-10 |
| Cloud Logging | $5-15 | $10-40 |
| Cloud Monitoring | $5-15 | $10-30 |
| Cloud Trace | $2-5 | $5-15 |
| Vertex AI | $0 (minimal) | $50-200 |
| **TOTAL** | **$204-460/month** | **$585-1,975/month** |

### Annual Projection

- **Development**: $2,448-5,520/year
- **Production**: $7,020-23,700/year

**Average Production Cost**: ~$12,000-15,000/year

---

## 🎯 Google Cloud's Contributions to the Project

### 1. Rapid Development

**Serverless Architecture**: Ability to focus solely on code development without spending time on infrastructure management.

**Managed Services**: Maintenance of services like database, caching, and messaging is handled by Google.

**Infrastructure as Code**: All infrastructure is managed as code with Terraform.

### 2. Cost Optimization

**Scale-to-Zero**: No payment for unused services.

**Pay-per-Use**: Charged only for actual usage.

**Free Tier**: Generous free tier for many services.

### 3. Security and Compliance

**Enterprise Security**: Google's security standards.

**Compliance**: GDPR, SOC 2, ISO 27001 certifications.

**Secret Management**: Secure credential management.

### 4. Scalability

**Auto-Scaling**: Automatic from 0 to hundreds of instances.

**Global Infrastructure**: Multi-region support for low latency.

**No Capacity Planning**: Google manages infrastructure.

### 5. AI/ML Capabilities

**Vertex AI**: Easy model deployment.

**Pre-trained Models**: Hugging Face integration.

**BigQuery ML**: Model training with SQL.

---

## 🚀 Future Plans and GCP Usage

### Short Term (3 months)

**New GCP Services**:
- [ ] **Cloud Functions**: Event-triggered microservices
- [ ] **Cloud Tasks**: Asynchronous task queuing
- [ ] **Cloud CDN**: Static asset delivery
- [ ] **Cloud Armor**: DDoS protection

**Expected Cost Increase**: +$100-200/month

### Medium Term (6 months)

**New Features**:
- [ ] **Memorystore (Redis)**: Advanced caching
- [ ] **Cloud Spanner**: Global database (multi-region)
- [ ] **Dataflow**: Real-time streaming pipeline
- [ ] **Cloud Vision API**: Image analysis

**Expected Cost Increase**: +$300-500/month

### Long Term (12 months)

**Enterprise Features**:
- [ ] **GKE (Kubernetes)**: Container orchestration
- [ ] **Cloud Composer**: Workflow orchestration
- [ ] **BigQuery BI Engine**: In-memory analytics
- [ ] **Multi-region deployment**: Global availability

**Expected Cost**: $2,000-3,000/month

---

## 📊 Why Google for Startups?

### 1. Financial Support

As a startup, the **$200,000 credit** offered by Google Cloud Platform is critical for developing and scaling our platform.

**Credit Usage Plan**:
- First 6 months: Development and testing ($2,000-3,000/month)
- 6-12 months: Production launch ($5,000-10,000/month)
- 12-24 months: Scale and growth ($10,000-15,000/month)

### 2. Technical Support

With support from Google's technical team:
- Architecture optimization
- Cost optimization
- Best practices implementation
- Performance tuning

### 3. Ecosystem

With other startups in the Google Cloud ecosystem:
- Networking
- Knowledge sharing
- Partnership opportunities

### 4. Credibility

Acceptance into Google for Startups program provides investors and customers:
- Trust signal
- Technical competency indicator
- Scale potential

---

## 🎨 Our Unique Aspects

### 1. AI-Assisted Development

This project was developed **entirely with AI assistance by an entrepreneur without coding knowledge**:

- All Python backend code written with AI
- Next.js frontend designed with AI
- Terraform infrastructure created with AI
- Microservices architecture planned with AI

**Result**: An enterprise-grade platform in just 6 months.

### 2. Full Google Cloud Adoption

Our project:
- Actively uses 14+ GCP services
- Implements best practices
- Leverages native integrations
- Exemplifies cloud-native architecture

### 3. Turkish FinTech Ecosystem

- First sentiment analysis platform in Turkey
- Compliant with CMB regulations
- Optimized for Turkish users
- Local data sources (CBRT, TURKSTAT)

---

## 📈 Success Metrics

### Technical Metrics

- ✅ **Uptime**: 99.9%+ (target)
- ✅ **Latency**: <500ms (p95)
- ✅ **Scale**: 0-100+ instances automatically
- ✅ **Data Processing**: 100K+ messages/day

### Business Metrics (Target)

- 🎯 **Users**: 1,000+ (first 6 months)
- 🎯 **API Calls**: 1M+ (monthly)
- 🎯 **Data Points**: 10M+ (monthly)
- 🎯 **Revenue**: $5K-10K MRR (12 months)

---

## 🤝 Our Contributions to Google Cloud

### 1. Case Study

Our platform can serve as an example for Google Cloud:
- AI-assisted development
- Serverless microservices
- Event-driven architecture
- FinTech use case

### 2. Community

- Blog posts (Medium, Dev.to)
- YouTube tutorials
- Open-source contributions
- Conference talks

### 3. Reference

When successful:
- Reference for other startups
- GCP adoption advocacy
- Case studies and testimonials

---

## 📞 Contact

**Project**: Sentilyze
**Founder**: [Name]
**Email**: team@sentilyze.live
**GitHub**: [Repository URL]
**Demo**: [Demo URL]

---

## 🙏 Conclusion

Sentilyze is a modern fintech platform that fully utilizes the power and flexibility of Google Cloud Platform. With Google for Startups program support:

- ✅ We can scale the platform
- ✅ We can reach more users
- ✅ We can develop new features
- ✅ We can strengthen the Turkish fintech ecosystem

**Google Cloud + AI-Assisted Development = Democratic Entrepreneurship**

We demonstrate that everyone can realize their big dreams, even without technical knowledge.

---

*This document was prepared for the Google for Startups Cloud Program application.*
*Last updated: February 2026*
