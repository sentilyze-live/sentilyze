# Sentilyze - Technical Architecture and Tech Stack Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Design](#architecture-design)
4. [Microservices](#microservices)
5. [Data Flow](#data-flow)
6. [Infrastructure](#infrastructure)
7. [Security](#security)
8. [Scalability](#scalability)

---

## 🎯 Overview

Sentilyze is a fully scalable sentiment analysis platform using **event-driven microservices architecture**, running on Google Cloud Platform.

### Key Features

- ✅ **Microservices Architecture**: 8 independent services
- ✅ **Event-Driven**: Asynchronous communication via Pub/Sub
- ✅ **Serverless**: Auto-scaling with Cloud Run
- ✅ **AI/ML Powered**: Vertex AI, Hugging Face, OpenAI integration
- ✅ **Real-Time**: Minute-level data processing
- ✅ **Cloud-Native**: Full GCP integration
- ✅ **Infrastructure as Code**: Terraform management

---

## 💻 Technology Stack

### Backend

#### Programming Languages
- **Python 3.11+**: Main backend language
- **TypeScript**: Frontend and API routes

#### Web Frameworks
- **FastAPI**: All microservices
- **Uvicorn**: ASGI server
- **Next.js 14**: Frontend framework (App Router)

#### Data Processing
- **Pandas**: Data manipulation
- **NumPy**: Numerical computations
- **Beautiful Soup**: Web scraping

### Frontend

#### Framework and Libraries
- **Next.js 14**: React framework (App Router)
- **React 18**: UI library
- **TypeScript**: Type safety
- **Tailwind CSS**: Utility-first CSS
- **shadcn/ui**: Component library

#### State Management
- **React Context**: Feature flags
- **React Query**: Server state (planned)

### AI/ML Stack

#### NLP Models
- **Hugging Face Transformers**
  - `cardiffnlp/twitter-roberta-base-sentiment-latest`
  - `ProsusAI/finbert` (financial sentiment)
- **OpenAI GPT-4**: Complex analysis (optional)
- **Google Vertex AI**: Model hosting

#### ML Frameworks
- **TensorFlow/Keras**: Time series models (planned)
- **scikit-learn**: Traditional ML
- **ARIMA**: Statistical forecasting

### Google Cloud Platform

#### Compute
- **Cloud Run**: Serverless container hosting
- **Cloud Functions**: Event-triggered functions (future)
- **Cloud Scheduler**: Scheduled tasks

#### Storage
- **BigQuery**: Data warehouse and analytics
- **Cloud SQL (PostgreSQL)**: Relational data
- **Cloud Storage**: Object storage (models, logs)
- **Firestore**: NoSQL cache and session storage

#### Messaging
- **Cloud Pub/Sub**: Event streaming
  - Push subscriptions: Cloud Run compatible
  - Pull subscriptions: Batch processing

#### AI/ML
- **Vertex AI**: Model hosting and inference
- **AI Platform**: Model training (planned)

#### Security & Ops
- **Secret Manager**: API keys and credentials
- **Cloud Build**: CI/CD pipeline
- **Cloud Logging**: Centralized log management
- **Cloud Monitoring**: Metrics and alerts
- **Cloud Trace**: Distributed tracing
- **Artifact Registry**: Container registry

### DevOps & Infrastructure

#### Infrastructure as Code
- **Terraform 1.5+**: Complete infrastructure management
- **Modular structure**: Pub/Sub, BigQuery modules

#### CI/CD
- **Cloud Build**: Automated build and deploy
- **Docker**: Containerization
- **Multi-stage builds**: Optimized images

#### Monitoring
- **Prometheus Client**: Metric collection
- **structlog**: Structured logging
- **Cloud Monitoring**: GCP native monitoring

### Data Sources

#### Crypto Market Data
- **Binance API**: Real-time price data
- **CoinGecko**: Market data
- **CryptoCompare**: Historical data
- **Finnhub**: Financial data

#### Gold Market Data
- **Gold API**: Spot prices
- **Metals API**: Precious metals data
- **FRED (Federal Reserve)**: Macroeconomic data
- **TCMB**: Turkish central bank data

#### Social Media & News
- **Twitter API v2**: Tweets
- **Reddit API (PRAW)**: Reddit posts
- **RSS Feeds**: News sites
- **NewsAPI**: News aggregation
- **LunarCrush**: Social metrics
- **Santiment**: On-chain and social data

### Database Schemas

#### BigQuery Tables
1. **raw_data**: Raw data
2. **sentiment_analysis**: Processed sentiment
3. **market_context**: Technical indicators
4. **predictions**: Forecasts
5. **prediction_accuracy**: Accuracy metrics
6. **alerts**: Notification history
7. **analytics_summary**: Daily summaries

#### PostgreSQL
- **predictions**: Prediction tracking
- **users**: User management (admin panel)
- **feature_flags**: Feature flags
- **api_keys**: API keys

---

## 🏗️ Architecture Design

### Microservices Architecture

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

| Topic | Publisher | Subscribers | Purpose |
|-------|-----------|-------------|---------|
| `raw-events` | Ingestion | Sentiment Processor | Raw market/social data |
| `processed-sentiment` | Sentiment | Context Processor | Analyzed sentiment |
| `market-context` | Context | Prediction Engine | Enriched market data |
| `predictions` | Prediction | Alert, Tracker, Analytics | Forecasts |
| `alerts` | Alert Service | - | Notifications |
| `analytics-events` | All services | Analytics Engine | Usage metrics |

---

## 🔧 Microservices

### 1. API Gateway (Port 8080)

**Responsibility**: Single entry point for all client requests

**Technologies**:
- FastAPI
- JWT Authentication
- Rate Limiting (Firestore-based)
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

**Dependencies**:
- Firestore (cache)
- BigQuery (queries)
- Secret Manager

### 2. Ingestion Service (Port 8081)

**Responsibility**: Data collection from external sources

**Technologies**:
- FastAPI
- APScheduler (scheduled tasks)
- aiohttp (async HTTP)
- PRAW (Reddit)

**Data Sources**:
- Crypto: Binance, CoinGecko, CryptoCompare, Finnhub
- Gold: Gold API, Metals API, FRED
- Social: Twitter API, Reddit
- News: RSS feeds, NewsAPI

**Features**:
- Cost tracking (API usage monitoring)
- Rate limiting
- Error handling and retry logic
- Data normalization

**Triggers**:
- Cloud Scheduler (every 5 min - crypto)
- Cloud Scheduler (every 15 min - gold)

### 3. Sentiment Processor (Port 8082)

**Responsibility**: NLP sentiment analysis

**Technologies**:
- Hugging Face Transformers
- Vertex AI (OpenAI integration)
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

**Responsibility**: Technical analysis and market indicators

**Technologies**:
- pandas (data manipulation)
- NumPy (calculations)
- TA-Lib (planned)

**Indicators**:
- **Trend**: MA20, MA50, MA200, EMA
- **Momentum**: RSI, MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, VWAP

**Market-Specific**:
- **Crypto**: Fear & Greed Index, on-chain metrics
- **Gold**: USD correlation, treasury yields

### 5. Prediction Engine (Port 8084)

**Responsibility**: ML-based price forecasts

**Technologies**:
- TensorFlow/Keras (planned)
- scikit-learn
- ARIMA

**Model Architecture** (Planned):
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

**Responsibility**: User notifications

**Channels**:
- Email (SMTP)
- Slack (webhooks)
- Discord (webhooks)
- Telegram (planned)

**Triggers**:
- High confidence predictions (>80%)
- Sentiment shifts (>20 points)
- Price volatility spikes

### 7. Tracker Service (Port 8087)

**Responsibility**: Prediction accuracy tracking

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

**Responsibility**: Reporting and analysis

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

## 🔄 Data Flow

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

---

## 🏢 Infrastructure

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
- Development: All services
- Production: Only Alert, Tracker, Analytics

---

## 🔒 Security

### Authentication & Authorization

**API Gateway**:
- JWT tokens
- API key validation
- Rate limiting per user

**Service-to-Service**:
- IAM service accounts
- Least privilege principle

**External APIs**:
- API keys in Secret Manager
- Automatic rotation (planned)

### Data Security

**Encryption**:
- At rest: Cloud KMS
- In transit: TLS 1.3
- Secrets: Secret Manager

**PII Handling**:
- No personal data stored
- Market data only
- GDPR compliant

---

## 📈 Scalability

### Horizontal Scaling

**Independent Service Scaling**:
- Each service scales based on its own traffic
- CPU and memory-based auto-scaling
- Min 0, Max 100 instances

### Performance Optimization

**Caching Strategy**:
- L1: In-memory (Python dictionaries)
- L2: Firestore (5 min TTL)
- L3: BigQuery BI Engine

**Async Processing**:
- Non-blocking I/O (aiohttp)
- Concurrent API calls
- Batch processing for BigQuery

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

### Deployment Strategy

**Blue-Green Deployment**:
- Deploy new version with --no-traffic
- Health check
- Gradual traffic migration
- Rollback capability

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
- [ ] Multi-region deployment

### Long Term (12 months)
- [ ] Real-time streaming (Apache Beam)
- [ ] Advanced ML models (Transformers)
- [ ] Algorithmic trading API

---

*Last updated: February 2026*
*Version: 4.0.0*
