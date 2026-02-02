# Sentilyze Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Service Architecture](#service-architecture)
4. [Data Flow](#data-flow)
5. [Data Storage](#data-storage)
6. [Event Streaming](#event-streaming)
7. [Machine Learning Pipeline](#machine-learning-pipeline)
8. [Security](#security)
9. [Scalability & Performance](#scalability--performance)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

Sentilyze is a distributed, event-driven microservices architecture built on Google Cloud Platform. It processes real-time market data and social sentiment to generate price predictions with confidence scoring.

### Design Principles

1. **Event-Driven**: Asynchronous processing via Pub/Sub for loose coupling
2. **Cloud-Native**: Serverless components for automatic scaling
3. **Multi-Market**: Unified architecture supporting diverse asset types
4. **Data-Driven**: All decisions backed by historical data analysis
5. **Resilient**: Graceful degradation and automatic recovery

### High-Level Component Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                   │
├────────────────────────────────────────────────────────────────────────────┤
│  Mobile Apps  │  Web Dashboard  │  External APIs  │  Trading Bots          │
└───────────────┴─────────────────┴─────────────────┴────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (Cloud Run)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  REST API    │  │  Auth/JWT    │  │ Rate Limiter │  │   Router     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     DATA INGESTION SERVICE                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  Crypto  │ │   Gold   │ │ Twitter  │ │  Reddit  │ │   News   │  │   │
│  │  │  APIs    │ │   APIs   │ │   API    │ │   API    │ │   APIs   │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ Pub/Sub: raw-market-data                   │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │                   SENTIMENT PROCESSOR                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   Hugging    │  │    OpenAI    │  │   Custom     │              │   │
│  │  │   Face       │  │   (GPT-4)    │  │   Models     │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ Pub/Sub: processed-sentiment               │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │                 MARKET CONTEXT PROCESSOR                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  Technical   │  │   Market     │  │  Correlation │              │   │
│  │  │  Indicators  │  │   Metrics    │  │   Analysis   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ Pub/Sub: market-context                    │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │                    PREDICTION ENGINE                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │    LSTM      │  │    ARIMA     │  │  Ensemble    │              │   │
│  │  │    Model     │  │    Model     │  │   Voting     │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
└─────────────────────────────────┼──────────────────────────────────────────┘
                                  │ Pub/Sub: predictions
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │    ALERT     │ │   TRACKER    │ │  ANALYTICS   │
        │   SERVICE    │ │   SERVICE    │ │   ENGINE     │
        └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Architecture Patterns

### 1. Event-Driven Architecture (EDA)

Services communicate asynchronously through Google Pub/Sub topics:

```
Raw Data → Sentiment → Context → Predictions → Actions
```

**Benefits:**
- Loose coupling between services
- Independent scaling
- Fault tolerance (retry and dead-letter queues)
- Replay capability for debugging

### 2. CQRS (Command Query Responsibility Segregation)

**Write Path (Event Stream):**
```
Ingestion → Pub/Sub → BigQuery (raw data storage)
```

**Read Path (Query APIs):**
```
Analytics Engine → BigQuery Views → API Response
```

### 3. Saga Pattern

For multi-step prediction validation:

```
1. Prediction Generated
2. Wait for Time Horizon
3. Validate Against Actual Price
4. Update Accuracy Metrics
5. Retrain Model if Needed
```

---

## Service Architecture

### 1. API Gateway

**Purpose:** Single entry point for all client requests

**Components:**
- REST API endpoints
- JWT authentication
- Rate limiting
- Request routing
- Response caching

**Key Endpoints:**
```
GET  /api/v1/markets/overview           # Market summary
GET  /api/v1/sentiment/{market}/{asset} # Sentiment data
GET  /api/v1/predictions/{market}       # Active predictions
GET  /api/v1/analytics/accuracy         # Model performance
POST /api/v1/alerts/subscribe          # Subscribe to alerts
```

### 2. Data Ingestion Service

**Purpose:** Collect data from multiple external sources

**Architecture:**
```
┌─────────────────────────────────────────┐
│         Ingestion Service               │
├─────────────────────────────────────────┤
│  Scheduler (Cloud Scheduler)            │
│         │                               │
│    ┌────▼────┐                          │
│    │ Fetchers │                          │
│    └────┬────┘                          │
│  ┌──────┼──────┐                        │
│  ▼      ▼      ▼                        │
│ Crypto  Gold  Social                     │
│  │      │      │                         │
│  └──────┼──────┘                        │
│         ▼                               │
│   ┌───────────┐                         │
│   │Normalizer │                         │
│   └─────┬─────┘                         │
│         ▼                               │
│   Pub/Sub: raw-market-data              │
└─────────────────────────────────────────┘
```

**Data Sources:**
- **Crypto**: CoinMarketCap, CoinAPI
- **Gold**: Gold API, Metals API
- **Social**: Twitter API v2, Reddit API
- **News**: NewsAPI, RSS feeds

### 3. Sentiment Processor

**Purpose:** NLP analysis of social and news content

**Pipeline:**
```
Raw Text → Preprocessing → Model Inference → Post-processing → Enrichment
```

**Models:**
- **Primary**: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- **Secondary**: `finbert-tone` (financial domain)
- **Tertiary**: OpenAI GPT-4 (complex context)

**Enrichments:**
- Entity extraction (assets, people, organizations)
- Keyword extraction
- Emotion detection (joy, anger, fear, etc.)
- Subjectivity scoring

### 4. Market Context Processor

**Purpose:** Technical analysis and market indicator calculation

**Indicators:**
- **Trend**: Moving averages (MA20, MA50, MA200), EMA
- **Momentum**: RSI, MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, VWAP
- **Support/Resistance**: Pivot points

**Gold-Specific:**
- USD strength correlation
- Treasury yield impact
- Inflation expectation

**Crypto-Specific:**
- Fear & Greed Index
- Network metrics (hash rate, active addresses)
- On-chain analysis

### 5. Prediction Engine

**Purpose:** Generate price predictions using ML models

**Architecture:**
```
┌─────────────────────────────────────────────┐
│           Prediction Engine                  │
├─────────────────────────────────────────────┤
│                                              │
│  Input Features                              │
│  ┌─────────────┬─────────────┬────────────┐ │
│  │   Sentiment │   Technical │  Market    │ │
│  │   Score     │  Indicators │  Context   │ │
│  └─────────────┴─────────────┴────────────┘ │
│              │                               │
│              ▼                               │
│  ┌──────────────────────────────────────┐   │
│  │         Feature Engineering          │   │
│  │  - Scaling                           │   │
│  │  - Encoding                          │   │
│  │  - Windowing                         │   │
│  └──────────────────┬───────────────────┘   │
│                     │                        │
│     ┌───────────────┼───────────────┐       │
│     ▼               ▼               ▼       │
│  ┌────────┐    ┌────────┐    ┌────────┐    │
│  │  LSTM  │    │ ARIMA  │    │ Linear │    │
│  │  Model │    │ Model  │    │  Reg   │    │
│  └───┬────┘    └───┬────┘    └───┬────┘    │
│      │             │             │          │
│      └─────────────┼─────────────┘          │
│                    ▼                        │
│           ┌──────────────┐                  │
│           │   Ensemble   │                  │
│           │    Voting    │                  │
│           └──────┬───────┘                  │
│                  ▼                          │
│  ┌──────────────────────────────────────┐   │
│  │         Output Generation            │   │
│  │  - Predicted Direction (Up/Down)     │   │
│  │  - Confidence Score                  │   │
│  │  - Probability Distribution          │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Models:**
- **LSTM**: Deep learning for sequential patterns
- **ARIMA**: Time-series forecasting
- **XGBoost**: Gradient boosting for feature importance
- **Ensemble**: Weighted voting for final prediction

**Training:**
- Retraining triggered on schedule (weekly) or accuracy degradation
- Historical data from BigQuery
- Validation on holdout set

### 6. Alert Service

**Purpose:** Notify users of significant events

**Triggers:**
- High-confidence predictions (>80%)
- Sentiment shifts (>20 point change)
- Price volatility spikes
- Model accuracy degradation

**Channels:**
- Email (SMTP)
- Slack (webhooks)
- Discord (webhooks)
- SMS (Twilio - future)

### 7. Tracker Service

**Purpose:** Validate predictions and track accuracy

**Process:**
1. Store prediction in PostgreSQL
2. Wait for prediction horizon (e.g., 24 hours)
3. Fetch actual price at validation time
4. Compare predicted vs actual
5. Calculate accuracy metrics
6. Update BigQuery with results

**Metrics:**
- Direction accuracy (% correct up/down predictions)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Square Error)
- Sharpe ratio (risk-adjusted returns)

### 8. Analytics Engine

**Purpose:** Generate reports and insights

**Capabilities:**
- Historical analysis (daily, weekly, monthly)
- Market correlation analysis
- Model performance dashboards
- Custom report generation

**Optimization:**
- Query caching with Redis (5-minute TTL)
- BigQuery materialized views
- Pre-aggregated summary tables

---

## Data Flow

### Complete Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION                                     │
│  Time: Every 5 min (crypto), Every 15 min (gold), Real-time (social)    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  External APIs → Normalization → Validation → Pub/Sub: raw-market-data  │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      SENTIMENT PROCESSING                                 │
│  Time: Real-time (streaming)                                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Raw Text → Preprocessing → Model Inference → Enrichment                │
│                ↓              ↓               ↓                          │
│           Tokenization    Sentiment      Entity/Keyword                 │
│           Cleaning        Score          Extraction                     │
│           Stopword        Confidence     Emotions                       │
│           Removal         Label                                             │
│                                                                          │
│  Output → Pub/Sub: processed-sentiment                                   │
│         → BigQuery: sentiment_analysis                                   │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     MARKET CONTEXT PROCESSING                             │
│  Time: Real-time (streaming)                                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Price Data → Technical Analysis → Context Enrichment                    │
│     ↓            ↓                    ↓                                  │
│  Current      Indicators           Market Metrics                       │
│  Price        (RSI, MACD,          (Volume, Dominance                  │
│  History      Bollinger)           Fear/Greed)                          │
│                                                                          │
│  Output → Pub/Sub: market-context                                        │
│         → BigQuery: market_context                                       │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      PREDICTION GENERATION                                │
│  Time: Real-time (streaming)                                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Sentiment + Context → Feature Engineering → Model Prediction           │
│         ↓                  ↓                    ↓                        │
│  Aggregated           Scaling/            Ensemble                      │
│  Scores               Encoding            Voting                        │
│                       Windowing                                          │
│                                                                          │
│  Output → Pub/Sub: predictions                                           │
│         → PostgreSQL: predictions (tracking)                            │
│         → BigQuery: predictions (analytics)                             │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ALERT SERVICE  │    │ TRACKER SERVICE │    │ANALYTICS ENGINE │
│                 │    │                 │    │                 │
│ Evaluate Triggers│    │ Store Prediction│    │ Update Metrics  │
│ Send Notifications│   │ Wait for Horizon│    │ Generate Reports│
│                 │    │ Validate Result │    │ Cache Results   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Data Storage

### Storage Strategy

| Data Type | Storage | Purpose | Retention |
|-----------|---------|---------|-----------|
| **Raw Data** | BigQuery | Analytics, ML training | 90 days |
| **Sentiment** | BigQuery | Analysis, reporting | 1 year |
| **Predictions** | PostgreSQL + BigQuery | Tracking, validation | Indefinite |
| **Accuracy** | BigQuery | Model improvement | Indefinite |
| **Cache** | Redis | Performance | TTL-based |
| **Models** | Cloud Storage | ML model artifacts | Versioned |

### BigQuery Schema

See [schemas directory](./infrastructure/terraform/schemas/) for detailed table schemas.

Key tables:
- `raw_data`: All ingested market and social data
- `sentiment_analysis`: Processed sentiment with scores
- `market_context`: Technical indicators and market metrics
- `predictions`: All generated predictions
- `prediction_accuracy`: Validated predictions with accuracy metrics
- `alerts`: Alert history and delivery status
- `analytics_summary`: Pre-aggregated daily summaries

### PostgreSQL Schema (Prediction Tracking)

```sql
-- predictions table
CREATE TABLE predictions (
    id UUID PRIMARY KEY,
    market_type VARCHAR(20) NOT NULL,
    asset_symbol VARCHAR(10) NOT NULL,
    prediction_timestamp TIMESTAMP NOT NULL,
    prediction_type VARCHAR(50) NOT NULL,
    prediction_horizon_hours INTEGER NOT NULL,
    current_price DECIMAL(18, 8) NOT NULL,
    predicted_price DECIMAL(18, 8),
    predicted_direction VARCHAR(10) NOT NULL,
    predicted_change_percent DECIMAL(8, 4),
    confidence_score DECIMAL(4, 3) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    validated BOOLEAN DEFAULT FALSE,
    validation_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX idx_predictions_market ON predictions(market_type, asset_symbol);
CREATE INDEX idx_predictions_timestamp ON predictions(prediction_timestamp);
CREATE INDEX idx_predictions_validated ON predictions(validated) WHERE validated = FALSE;
```

---

## Event Streaming

### Pub/Sub Topics

| Topic | Publisher | Subscribers | Purpose |
|-------|-----------|-------------|---------|
| `raw-market-data` | Ingestion | Sentiment Processor | Raw market/social data |
| `processed-sentiment` | Sentiment Processor | Context Processor | Analyzed sentiment |
| `market-context` | Context Processor | Prediction Engine | Enriched market data |
| `predictions` | Prediction Engine | Alert, Tracker, Analytics | Generated predictions |
| `alerts` | Alert Service | - | Alert notifications |
| `analytics-events` | All services | Analytics Engine | Usage/performance metrics |

### Message Schema

**Raw Market Data Message:**
```json
{
  "id": "uuid",
  "market_type": "crypto",
  "asset_symbol": "BTC",
  "data_source": "coinmarketcap",
  "data_type": "price",
  "timestamp": "2024-01-15T10:30:00Z",
  "price": 45000.50,
  "volume": 1234567890,
  "metadata": {...}
}
```

**Sentiment Message:**
```json
{
  "id": "uuid",
  "raw_data_id": "uuid",
  "market_type": "crypto",
  "asset_symbol": "BTC",
  "sentiment_score": 0.75,
  "sentiment_label": "positive",
  "confidence": 0.92,
  "keywords": ["bullish", "breakout", "moon"],
  "processed_at": "2024-01-15T10:30:05Z"
}
```

**Prediction Message:**
```json
{
  "id": "uuid",
  "market_context_id": "uuid",
  "market_type": "crypto",
  "asset_symbol": "BTC",
  "prediction_timestamp": "2024-01-15T10:31:00Z",
  "predicted_direction": "up",
  "predicted_change_percent": 2.5,
  "confidence_score": 0.78,
  "prediction_horizon_hours": 24,
  "model_version": "v2.1.0"
}
```

---

## Machine Learning Pipeline

### Model Development Lifecycle

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Data    │ →  │ Feature  │ →  │  Train   │ →  │ Evaluate │ →  │ Deploy   │
│  Prep    │    │ Engineer │    │  Model   │    │  Model   │    │  Model   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
      ↑                                                          │
      └──────────────────── Retrain Trigger ←────────────────────┘
                   (Scheduled or Accuracy Drop)
```

### Feature Engineering

**Features Used:**
1. **Sentiment Features**
   - Aggregated sentiment score (rolling 1h, 6h, 24h)
   - Sentiment momentum (rate of change)
   - Sentiment volatility
   - Volume of mentions

2. **Technical Features**
   - Normalized price (0-1 scale)
   - Price momentum (returns)
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - Bollinger Bands position

3. **Market Features**
   - Volume trends
   - Market cap changes
   - Volatility index
   - Fear & Greed Index (crypto)
   - USD strength (gold)

### Model Architecture

**LSTM Model:**
```python
# Simplified architecture
Input (sequence_length=24, features=15)
    ↓
LSTM Layer 1 (128 units, return_sequences=True)
    ↓
Dropout (0.2)
    ↓
LSTM Layer 2 (64 units)
    ↓
Dropout (0.2)
    ↓
Dense Layer 1 (32 units, ReLU)
    ↓
Dense Layer 2 (3 units, Softmax)  # [up, down, sideways]
```

**Ensemble Strategy:**
```
Final Prediction = Σ(weight_i × prediction_i) / Σ(weights)

Where weights are based on recent accuracy:
weight_i = accuracy_i / Σ(accuracies)
```

---

## Security

### Authentication & Authorization

- **API Gateway**: JWT token validation
- **Service-to-Service**: IAM service accounts
- **External APIs**: API keys stored in Secret Manager

### Data Security

- **Encryption at Rest**: Cloud KMS for sensitive data
- **Encryption in Transit**: TLS 1.3 for all communications
- **PII Handling**: No personal data stored (market data only)

### Network Security

- **VPC**: Private Google Access for Cloud SQL
- **Firewall**: Restricted ingress/egress rules
- **Cloud Armor**: DDoS protection and WAF rules

---

## Scalability & Performance

### Auto-Scaling Strategy

| Service | Min Instances | Max Instances | Scaling Trigger |
|---------|---------------|---------------|-----------------|
| API Gateway | 2 | 50 | Request count > 100/sec |
| Ingestion | 1 | 20 | CPU > 70% |
| Sentiment | 1 | 100 | Pub/Sub backlog > 1000 |
| Context | 1 | 50 | Pub/Sub backlog > 1000 |
| Prediction | 1 | 50 | Pub/Sub backlog > 1000 |
| Alert | 0 | 20 | Pub/Sub backlog > 100 |
| Tracker | 1 | 10 | Schedule-based |
| Analytics | 0 | 10 | Request count |

### Performance Optimizations

1. **Caching**
   - Redis for query results (5-minute TTL)
   - BigQuery BI Engine for analytics queries
   - Cloud CDN for static assets

2. **Database**
   - BigQuery partitioning (daily) and clustering
   - PostgreSQL indexes on frequently queried columns
   - Connection pooling (Cloud SQL Proxy)

3. **Processing**
   - Batch processing for sentiment (10 messages/batch)
   - Async I/O for external API calls
   - Parallel model inference

---

## Deployment Architecture

### Environments

```
┌─────────────────────────────────────────────────────────┐
│                     DEVELOPMENT                          │
│  Local Docker Compose with emulators                     │
│  • BigQuery Emulator                                     │
│  • Pub/Sub Emulator                                      │
│  • Local Redis & PostgreSQL                              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     STAGING                              │
│  GCP Project: sentilyze-staging                          │
│  • Shared Cloud Run services                             │
│  • Reduced Redis instance                                │
│  • Development BigQuery dataset                          │
│  • Automatic deployments from develop branch             │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     PRODUCTION                           │
│  GCP Project: sentilyze-v5-clean                         │
│  • High-availability Cloud Run                           │
│  • HA Redis (Standard tier)                              │
│  • Production BigQuery dataset                           │
│  • Manual approval for deployments                       │
└─────────────────────────────────────────────────────────┘
```

### CI/CD Pipeline

```
Developer Push → GitHub → Cloud Build → Tests → Build → Deploy
                              ↓
                    Branch Detection:
                    • main → Production
                    • develop → Staging
                    • feature/* → Dev Environment
```

### Infrastructure as Code

All infrastructure managed via Terraform:
- Service accounts and IAM
- Pub/Sub topics and subscriptions
- BigQuery datasets and tables
- Cloud Run services
- Cloud Scheduler jobs
- Monitoring and alerting

---

## Future Enhancements

1. **Real-time Streaming**: Apache Beam for lower latency
2. **Advanced Models**: Transformer-based time series (Autoformer, PatchTST)
3. **Multi-asset Correlation**: Cross-asset prediction models
4. **Futures/Options**: Derivatives market integration
5. **Mobile App**: React Native mobile application
6. **Backtesting Framework**: Historical simulation engine
7. **A/B Testing**: Model comparison framework

---

## Conclusion

Sentilyze's architecture provides a robust, scalable, and maintainable platform for market sentiment analysis. The event-driven design enables independent scaling of components, while the data-first approach ensures all predictions are backed by comprehensive historical analysis.

For deployment details, see [DEPLOYMENT.md](DEPLOYMENT.md).
