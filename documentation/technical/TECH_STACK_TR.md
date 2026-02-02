# Sentilyze - Teknik Mimari ve Tech Stack Dökümanı

## 📋 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Teknoloji Yığını](#teknoloji-yığını)
3. [Mimari Tasarım](#mimari-tasarım)
4. [Mikroservisler](#mikroservisler)
5. [Veri Akışı](#veri-akışı)
6. [Altyapı](#altyapı)
7. [Güvenlik](#güvenlik)
8. [Ölçeklenebilirlik](#ölçeklenebilirlik)

---

## 🎯 Genel Bakış

Sentilyze, **event-driven mikroservis mimarisi** kullanan, Google Cloud Platform üzerinde çalışan, tam ölçeklenebilir bir duygu analizi platformudur.

### Temel Özellikler

- ✅ **Mikroservis Mimarisi**: 8 bağımsız servis
- ✅ **Event-Driven**: Pub/Sub ile asenkron iletişim
- ✅ **Serverless**: Cloud Run ile otomatik ölçeklendirme
- ✅ **AI/ML Destekli**: Vertex AI, Hugging Face, OpenAI entegrasyonu
- ✅ **Gerçek Zamanlı**: Dakika bazında veri işleme
- ✅ **Cloud-Native**: Tam GCP entegrasyonu
- ✅ **Infrastructure as Code**: Terraform ile yönetim

---

## 💻 Teknoloji Yığını

### Backend

#### Programlama Dilleri
- **Python 3.11+**: Ana backend dili
- **TypeScript**: Frontend ve API routes

#### Web Frameworkler
- **FastAPI**: Mikroservislerin tamamı
- **Uvicorn**: ASGI server
- **Next.js 14**: Frontend framework (App Router)

#### Veri İşleme
- **Pandas**: Veri manipülasyonu
- **NumPy**: Sayısal hesaplamalar
- **Beautiful Soup**: Web scraping

### Frontend

#### Framework ve Kütüphaneler
- **Next.js 14**: React framework (App Router)
- **React 18**: UI library
- **TypeScript**: Type safety
- **Tailwind CSS**: Utility-first CSS
- **shadcn/ui**: Component library

#### State Management
- **React Context**: Feature flags
- **React Query**: Server state (planlanan)

### AI/ML Stack

#### NLP Models
- **Hugging Face Transformers**
  - `cardiffnlp/twitter-roberta-base-sentiment-latest`
  - `ProsusAI/finbert` (finansal sentiment)
- **OpenAI GPT-4**: Karmaşık analiz (opsiyonel)
- **Google Vertex AI**: Model hosting

#### ML Frameworks
- **TensorFlow/Keras**: Zaman serisi modelleri (planlanan)
- **scikit-learn**: Geleneksel ML
- **ARIMA**: İstatistiksel tahminleme

### Google Cloud Platform

#### Compute
- **Cloud Run**: Serverless container hosting
- **Cloud Functions**: Event-triggered functions (gelecek)
- **Cloud Scheduler**: Zamanlı görevler

#### Storage
- **BigQuery**: Veri ambarı ve analitik
- **Cloud SQL (PostgreSQL)**: İlişkisel veri
- **Cloud Storage**: Object storage (modeller, loglar)
- **Firestore**: NoSQL cache ve session storage

#### Messaging
- **Cloud Pub/Sub**: Event streaming
  - Push subscriptions: Cloud Run uyumlu
  - Pull subscriptions: Batch işleme

#### AI/ML
- **Vertex AI**: Model hosting ve inference
- **AI Platform**: Model training (planlanan)

#### Security & Ops
- **Secret Manager**: API keys ve credentials
- **Cloud Build**: CI/CD pipeline
- **Cloud Logging**: Merkezi log yönetimi
- **Cloud Monitoring**: Metrikler ve alertler
- **Cloud Trace**: Distributed tracing
- **Artifact Registry**: Container registry

### DevOps & Infrastructure

#### Infrastructure as Code
- **Terraform 1.5+**: Tüm altyapı yönetimi
- **Modüler yapı**: Pub/Sub, BigQuery modülleri

#### CI/CD
- **Cloud Build**: Otomatik build ve deploy
- **Docker**: Containerization
- **Multi-stage builds**: Optimize edilmiş image'lar

#### Monitoring
- **Prometheus Client**: Metrik toplama
- **structlog**: Yapılandırılmış loglama
- **Cloud Monitoring**: GCP native monitoring

### Data Sources

#### Crypto Market Data
- **Binance API**: Real-time fiyat verisi
- **CoinGecko**: Market data
- **CryptoCompare**: Geçmiş veriler
- **Finnhub**: Finansal data

#### Gold Market Data
- **Gold API**: Spot fiyatlar
- **Metals API**:귀금속 verileri
- **FRED (Federal Reserve)**: Makroekonomik data
- **TCMB**: Türk merkez bankası verileri

#### Social Media & News
- **Twitter API v2**: Tweets
- **Reddit API (PRAW)**: Reddit posts
- **RSS Feeds**: Haber siteleri
- **NewsAPI**: Haber aggregation
- **LunarCrush**: Sosyal metrikler
- **Santiment**: On-chain ve sosyal data

### Database Schemas

#### BigQuery Tables
1. **raw_data**: Ham veri
2. **sentiment_analysis**: İşlenmiş sentiment
3. **market_context**: Teknik göstergeler
4. **predictions**: Tahminler
5. **prediction_accuracy**: Doğruluk metrikleri
6. **alerts**: Bildirim geçmişi
7. **analytics_summary**: Günlük özetler

#### PostgreSQL
- **predictions**: Tahmin tracking
- **users**: Kullanıcı yönetimi (admin panel)
- **feature_flags**: Özellik bayrakları
- **api_keys**: API anahtarları

---

## 🏗️ Mimari Tasarım

### Mikroservis Mimarisi

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Web Dashboard │ Mobile App │ External APIs │ Trading Bots      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY (Port 8080)                      │
│  REST API │ Auth │ Rate Limiting │ Request Routing              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   INGESTION (Port 8081)                                  │   │
│  │   Crypto │ Gold │ Social Media │ News                     │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │ Pub/Sub: raw-events                            │
│  ┌──────────────▼───────────────────────────────────────────┐   │
│  │   SENTIMENT PROCESSOR (Port 8082)                        │   │
│  │   NLP │ Emotion Detection │ Entity Extraction            │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │ Pub/Sub: processed-sentiment                   │
│  ┌──────────────▼───────────────────────────────────────────┐   │
│  │   MARKET CONTEXT PROCESSOR (Port 8083)                   │   │
│  │   Technical Indicators │ Correlations                     │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │ Pub/Sub: market-context                        │
│  ┌──────────────▼───────────────────────────────────────────┐   │
│  │   PREDICTION ENGINE (Port 8084)                          │   │
│  │   ML Models │ Ensemble Voting                             │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │ Pub/Sub: predictions                           │
│                 │                                                │
│      ┌──────────┼──────────┬──────────────┐                     │
│      ▼          ▼          ▼              ▼                     │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐                 │
│  │ ALERT  │ │TRACKER │ │ANALYTICS│ │AGENT     │                 │
│  │(8085)  │ │(8087)  │ │(8086)   │ │GATEWAY   │                 │
│  └────────┘ └────────┘ └────────┘ └──────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Event-Driven Architecture

#### Event Flow
```
Raw Data → Sentiment → Context → Predictions → Actions
   ↓          ↓          ↓           ↓          ↓
BigQuery  BigQuery  BigQuery    PostgreSQL  External
                                 BigQuery    Services
```

#### Pub/Sub Topics

| Topic | Publisher | Subscribers | Amaç |
|-------|-----------|-------------|------|
| `raw-events` | Ingestion | Sentiment Processor | Ham market/sosyal veri |
| `processed-sentiment` | Sentiment | Context Processor | Analiz edilmiş sentiment |
| `market-context` | Context | Prediction Engine | Zenginleştirilmiş market data |
| `predictions` | Prediction | Alert, Tracker, Analytics | Tahminler |
| `alerts` | Alert Service | - | Bildirimler |
| `analytics-events` | Tüm servisler | Analytics Engine | Kullanım metrikleri |

---

## 🔧 Mikroservisler

### 1. API Gateway (Port 8080)

**Sorumluluk**: Tüm client isteklerinin tek giriş noktası

**Teknolojiler**:
- FastAPI
- JWT Authentication
- Rate Limiting (Firestore tabanlı)
- CORS handling

**Endpoints**:
```
GET  /api/v1/health
GET  /api/v1/markets/overview
GET  /api/v1/sentiment/{market}/{asset}
GET  /api/v1/predictions/{market}
GET  /api/v1/analytics/accuracy
POST /api/v1/alerts/subscribe
```

**Bağımlılıklar**:
- Firestore (cache)
- BigQuery (queries)
- Secret Manager

### 2. Ingestion Service (Port 8081)

**Sorumluluk**: External kaynaklardan veri toplama

**Teknolojiler**:
- FastAPI
- APScheduler (zamanlanmış görevler)
- aiohttp (async HTTP)
- PRAW (Reddit)

**Veri Kaynakları**:
- Crypto: Binance, CoinGecko, CryptoCompare, Finnhub
- Gold: Gold API, Metals API, FRED
- Social: Twitter API, Reddit
- News: RSS feeds, NewsAPI

**Özellikler**:
- Cost tracking (API kullanım takibi)
- Rate limiting
- Error handling ve retry logic
- Data normalization

**Tetikleyiciler**:
- Cloud Scheduler (her 5 dk - crypto)
- Cloud Scheduler (her 15 dk - gold)

### 3. Sentiment Processor (Port 8082)

**Sorumluluk**: NLP ile sentiment analizi

**Teknolojiler**:
- Hugging Face Transformers
- Vertex AI (OpenAI entegrasyonu)
- Semantic caching

**NLP Pipeline**:
1. **Preprocessing**: Tokenization, cleaning
2. **Model Inference**: Multi-model approach
3. **Post-processing**: Score normalization
4. **Enrichment**: Entity extraction, keywords

**Models**:
- Primary: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- Financial: `ProsusAI/finbert`
- Complex: GPT-4 (optional)

**Output**:
```json
{
  "sentiment_score": 0.75,
  "sentiment_label": "positive",
  "confidence": 0.92,
  "entities": ["Bitcoin", "Elon Musk"],
  "keywords": ["bullish", "breakout"],
  "emotions": {"joy": 0.8, "fear": 0.1}
}
```

### 4. Market Context Processor (Port 8083)

**Sorumluluk**: Teknik analiz ve market göstergeleri

**Teknolojiler**:
- pandas (data manipulation)
- NumPy (calculations)
- TA-Lib (planlanan)

**Indicators**:
- **Trend**: MA20, MA50, MA200, EMA
- **Momentum**: RSI, MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, VWAP

**Market-Specific**:
- **Crypto**: Fear & Greed Index, on-chain metrics
- **Gold**: USD correlation, treasury yields

### 5. Prediction Engine (Port 8084)

**Sorumluluk**: ML tabanlı fiyat tahminleri

**Teknolojiler**:
- TensorFlow/Keras (planlanan)
- scikit-learn
- ARIMA

**Model Architecture** (Planlanan):
```
Input Features (15)
    ↓
LSTM Layer 1 (128 units)
    ↓
Dropout (0.2)
    ↓
LSTM Layer 2 (64 units)
    ↓
Dense (32 units, ReLU)
    ↓
Output (3 classes: up, down, sideways)
```

**Ensemble Strategy**:
- Weighted voting
- Confidence scoring
- Model accuracy tracking

### 6. Alert Service (Port 8085)

**Sorumluluk**: Kullanıcı bildirimleri

**Channels**:
- Email (SMTP)
- Slack (webhooks)
- Discord (webhooks)
- Telegram (planlanan)

**Triggers**:
- High confidence predictions (>80%)
- Sentiment shifts (>20 points)
- Price volatility spikes

### 7. Tracker Service (Port 8087)

**Sorumluluk**: Tahmin doğruluğu takibi

**Process**:
1. Store prediction in PostgreSQL
2. Wait for time horizon
3. Fetch actual price
4. Calculate accuracy
5. Update metrics in BigQuery

**Metrics**:
- Direction accuracy (%)
- MAE (Mean Absolute Error)
- RMSE
- Sharpe ratio

### 8. Analytics Engine (Port 8086)

**Sorumluluk**: Raporlama ve analizler

**Features**:
- Historical analysis
- Correlation studies
- Performance dashboards
- Custom reports

**Optimization**:
- Redis/Firestore caching (5 min TTL)
- BigQuery materialized views
- Pre-aggregated tables

---

## 🔄 Veri Akışı

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: DATA COLLECTION (Every 5-15 min)                        │
├─────────────────────────────────────────────────────────────────┤
│ External APIs → Normalization → Validation → Pub/Sub: raw-events│
│                                                 ↓                │
│                                            BigQuery: raw_data    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: SENTIMENT ANALYSIS (Real-time streaming)                │
├─────────────────────────────────────────────────────────────────┤
│ Raw Text → NLP Models → Sentiment Scores → Pub/Sub              │
│                                              ↓                   │
│                                   BigQuery: sentiment_analysis   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: TECHNICAL ANALYSIS (Real-time)                          │
├─────────────────────────────────────────────────────────────────┤
│ Price Data → Technical Indicators → Context → Pub/Sub           │
│                                                  ↓               │
│                                      BigQuery: market_context    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: PREDICTION (Real-time)                                  │
├─────────────────────────────────────────────────────────────────┤
│ Features → ML Models → Ensemble → Pub/Sub: predictions          │
│                                        ↓                         │
│                          PostgreSQL + BigQuery: predictions      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
          ┌─────────────────┼─────────────────┐
          ↓                 ↓                 ↓
    ┌─────────┐       ┌─────────┐      ┌──────────┐
    │ ALERTS  │       │ TRACKER │      │ANALYTICS │
    └─────────┘       └─────────┘      └──────────┘
```

### Message Schemas

**Raw Data Message**:
```json
{
  "id": "uuid",
  "market_type": "crypto",
  "asset_symbol": "BTC",
  "data_source": "binance",
  "data_type": "price",
  "timestamp": "2026-02-01T10:30:00Z",
  "price": 45000.50,
  "volume": 1234567890,
  "metadata": {}
}
```

**Sentiment Message**:
```json
{
  "id": "uuid",
  "market_type": "crypto",
  "asset_symbol": "BTC",
  "sentiment_score": 0.75,
  "sentiment_label": "positive",
  "confidence": 0.92,
  "source": "twitter",
  "processed_at": "2026-02-01T10:30:05Z"
}
```

---

## 🏢 Altyapı

### Cloud Run Services

| Service | Min Instances | Max Instances | Memory | CPU |
|---------|---------------|---------------|--------|-----|
| API Gateway | 1 | 50 | 2Gi | 2 |
| Ingestion | 0 | 20 | 2Gi | 2 |
| Sentiment | 0 | 100 | 2Gi | 2 |
| Context | 0 | 50 | 2Gi | 2 |
| Prediction | 0 | 50 | 2Gi | 2 |
| Alert | 0 | 20 | 1Gi | 1 |
| Tracker | 0 | 10 | 1Gi | 1 |
| Analytics | 0 | 10 | 2Gi | 2 |

### Scaling Strategy

**Auto-scaling Triggers**:
- CPU > 70%
- Memory > 80%
- Request rate > 100/sec
- Pub/Sub backlog > 1000 messages

**Scale-to-Zero**:
- Development: Tüm servisler
- Production: Sadece Alert, Tracker, Analytics

### Database Configuration

**BigQuery**:
- Dataset: `sentilyze_dataset`
- Partition: Daily (timestamp field)
- Clustering: market_type, asset_symbol
- Retention: 90 days (raw), 1 year (processed)

**Cloud SQL (PostgreSQL)**:
- Version: PostgreSQL 15
- Instance: db-n1-standard-2 (prod) / db-f1-micro (dev)
- Backup: Daily at 03:00 UTC
- High Availability: Yes (prod)

**Firestore**:
- Mode: Native
- Location: europe-west3
- Usage: Cache, sessions, feature flags

---

## 🔒 Güvenlik

### Authentication & Authorization

**API Gateway**:
- JWT tokens
- API key validation
- Rate limiting per user

**Service-to-Service**:
- IAM service accounts
- Least privilege principle
- No inter-service authentication required (trusted VPC)

**External APIs**:
- API keys in Secret Manager
- Automatic rotation (planlanan)

### Data Security

**Encryption**:
- At rest: Cloud KMS
- In transit: TLS 1.3
- Secrets: Secret Manager

**PII Handling**:
- No personal data stored
- Market data only
- GDPR compliant

### Network Security

**VPC**:
- Private Google Access
- Cloud SQL private IP
- Firewall rules

**Cloud Armor** (Planlanan):
- DDoS protection
- WAF rules
- Rate limiting

---

## 📈 Ölçeklenebilirlik

### Horizontal Scaling

**Servislerin Bağımsız Ölçeklendirilmesi**:
- Her servis kendi trafiğine göre scale eder
- CPU ve memory tabanlı otomatik ölçeklendirme
- Min 0, Max 100 instance

### Vertical Scaling

**Resource Limits**:
- Production: 2 vCPU, 2Gi memory
- Development: 1 vCPU, 1Gi memory

### Performance Optimization

**Caching Strategy**:
- L1: In-memory (Python dictionaries)
- L2: Firestore (5 min TTL)
- L3: BigQuery BI Engine

**Database Optimization**:
- Partitioning by date
- Clustering by market/asset
- Materialized views
- Connection pooling

**Async Processing**:
- Non-blocking I/O (aiohttp)
- Concurrent API calls
- Batch processing for BigQuery

---

## 📊 Monitoring & Observability

### Metrics

**Application Metrics**:
- Request rate, latency, errors
- Processing time per service
- Pub/Sub message lag
- Cache hit rates

**Infrastructure Metrics**:
- CPU, memory utilization
- Network I/O
- Disk usage
- Database connections

### Logging

**Structured Logging** (structlog):
```python
logger.info(
    "prediction_generated",
    asset="BTC",
    confidence=0.85,
    direction="up",
    model_version="v2.1.0"
)
```

**Log Aggregation**:
- Cloud Logging
- Retention: 30 days
- Severity-based filtering

### Tracing

**Distributed Tracing** (Cloud Trace):
- Request flow across services
- Latency breakdown
- Error propagation

### Alerting

**Alert Conditions**:
- Error rate > 5%
- Latency > 2s (p95)
- Pub/Sub backlog > 10000
- Service down > 5 min

**Notification Channels**:
- Email
- Slack
- PagerDuty (planlanan)

---

## 🚀 Deployment

### CI/CD Pipeline

```
Code Push → GitHub → Cloud Build → Tests → Build Image → Deploy
                                      ↓
                            Branch Detection:
                            • main → Production
                            • develop → Staging
```

### Build Process

**Multi-stage Docker Build**:
1. Base: Python 3.11-slim
2. Dependencies: pip install
3. Copy code
4. Runtime user (non-root)

**Optimization**:
- Layer caching
- .dockerignore
- Minimal base images

### Deployment Strategy

**Blue-Green Deployment**:
- Deploy new version with --no-traffic
- Health check
- Gradual traffic migration
- Rollback capability

### Infrastructure as Code

**Terraform Modules**:
- `modules/pubsub`: Pub/Sub topics & subscriptions
- `modules/bigquery`: Dataset, tables, views

**State Management**:
- Backend: Google Cloud Storage
- Locking: Yes
- Encryption: Yes

---

## 📝 Development Workflow

### Local Development

**Docker Compose**:
```yaml
services:
  - pubsub-emulator
  - bigquery-emulator (planned)
  - postgres
  - firestore-emulator
  - redis (optional)
```

**Environment Setup**:
```bash
# Install dependencies
poetry install

# Start emulators
docker-compose up -d

# Run service
poetry run python -m services.api_gateway.src.main
```

### Testing

**Test Types**:
- Unit tests (pytest)
- Integration tests
- Load tests (locust - planlanan)

**Coverage Goal**: >80%

---

## 🔮 Future Roadmap

### Short Term (3 months)
- [ ] LSTM model implementation
- [ ] Backtesting framework
- [ ] Mobile app API
- [ ] WebSocket support

### Medium Term (6 months)
- [ ] Stock market integration
- [ ] Advanced correlation analysis
- [ ] A/B testing framework
- [ ] Multi-region deployment

### Long Term (12 months)
- [ ] Real-time streaming (Apache Beam)
- [ ] Advanced ML models (Transformers)
- [ ] Algorithmic trading API
- [ ] Community features

---

## 📚 Referanslar

### Teknolojiler
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Run](https://cloud.google.com/run)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest)

### AI/ML
- [Hugging Face](https://huggingface.co/)
- [Vertex AI](https://cloud.google.com/vertex-ai)

---

*Son güncelleme: Şubat 2026*
*Versiyon: 4.0.0*
