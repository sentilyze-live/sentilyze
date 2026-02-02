# Sentilyze Website Architecture Plan

## Executive Summary

This document provides a comprehensive architecture plan for the Sentilyze crypto lag sentiment analysis platform website. The focus is on creating a marketing/pitch website for Google Cloud Startup application with a hidden admin panel for cost control and a gold dashboard at `/altin`.

---

## 1. Website Structure & Routing

### 1.1 Public Marketing Pages

```
PUBLIC PAGES (Marketing/Pitch Focus: Crypto Lag Sentiment Analysis):
├── /                    → Landing page (Hero: Crypto Lag Sentiment)
│   ├── Hero Section: "Predict Crypto Moves Before They Happen"
│   ├── Lag Analysis Demo (Interactive visualization)
│   ├── Key Metrics (Accuracy, Lag Detection, Assets Tracked)
│   ├── How It Works (3-step process)
│   ├── Live Preview (Sample dashboard screenshot)
│   └── CTA Sections (Sign up, Contact)
│
├── /about               → About Sentilyze
│   ├── Mission & Vision
│   ├── The Lag Analysis Technology
│   ├── Team (optional for startup pitch)
│   └── Backed By (Google Cloud, etc.)
│
├── /product             → Product Features
│   ├── Lag Detection Engine
│   ├── Multi-Asset Support (Crypto + Gold)
│   ├── Real-time Sentiment Analysis
│   ├── Prediction Accuracy Tracking
│   └── API Access
│
├── /how-it-works        → Technical Explanation
│   ├── What is Sentiment Lag?
│   ├── Data Collection Pipeline
│   ├── ML Models (LSTM + ARIMA Ensemble)
│   ├── Correlation Analysis
│   └── Validation & Accuracy
│
├── /pricing             → Pricing Tiers
│   ├── Free Tier (Limited features)
│   ├── Pro Tier (Full dashboard access)
│   ├── Enterprise (API + Custom)
│   └── Feature Comparison Table
│
├── /case-studies        → Success Stories
│   ├── BTC Prediction Accuracy
│   ├── ETH Lag Detection Example
│   ├── Gold (XAU) Correlation Study
│   └── Metrics & ROI
│
├── /blog                → Technical Articles
│   ├── Understanding Crypto Sentiment Lag
│   ├── How Social Media Predicts Prices
│   ├── ML Models for Price Prediction
│   └── Market Analysis Reports
│
├── /docs                → API Documentation
│   ├── Getting Started
│   ├── Authentication
│   ├── Endpoints Reference
│   ├── WebSocket API
│   └── SDKs & Examples
│
└── /contact             → Contact Form
    ├── General Inquiries
    ├── Partnership Requests
    ├── Support
    └── Office Location (optional)
```

### 1.2 Dashboard Pages

```
DASHBOARD PAGES (Authenticated):
├── /altin               → Gold Dashboard (XAU/USD Analysis)
│   ├── Overview Tab     → Quick stats, sentiment timeline, predictions
│   ├── Sentiment Tab    → Sentiment gauge, distribution, emotions
│   ├── Predictions Tab  → Active predictions, accuracy metrics
│   ├── Market Tab       → Price charts, technical indicators
│   └── Sources Tab      → Data sources, quality metrics
│
└── /kripto              → Crypto Dashboard (Future - BTC, ETH, etc.)
    └── [Same structure as /altin]
```

### 1.3 Admin Panel (Hidden)

```
ADMIN PANEL (/admin/* - Requires Authentication):
├── /admin/login         → Admin login page
├── /admin/dashboard     → Overview & system health
├── /admin/feature-flags → CRITICAL: Cost control switches
├── /admin/users         → User management
├── /admin/api-keys      → API key management
├── /admin/budget        → Budget tracking & alerts
├── /admin/costs         → Detailed cost breakdown
├── /admin/services      → Microservice control
├── /admin/audit-logs    → Activity logs
└── /admin/settings      → System configuration
```

---

## 2. Feature Flag System Architecture

### 2.1 Feature Flag Model

```python
# Feature Flag Schema (PostgreSQL)
class FeatureFlag(Base):
    """Dynamic feature flags for cost control."""
    
    __tablename__ = "feature_flags"
    
    id: UUID (PK)
    key: str (unique, indexed)           # e.g., "ENABLE_REAL_TIME_WEBSOCKET"
    name: str                            # Human-readable name
    description: str                     # What this flag controls
    category: str                        # "cost_control", "feature", "experimental"
    
    # Value storage (typed)
    value_type: str                      # "boolean", "integer", "string", "json"
    default_value: JSONB                 # Default value
    current_value: JSONB                 # Current active value
    
    # Cost impact tracking
    estimated_daily_cost_usd: Decimal    # Estimated cost when enabled
    cost_category: str                   # "compute", "api", "storage", "network"
    
    # Control metadata
    is_enabled: bool                     # Master on/off switch
    requires_restart: bool               # Does service need restart?
    affected_services: list[str]         # Which microservices use this
    
    # Audit
    created_at: datetime
    updated_at: datetime
    updated_by: UUID                     # Admin user who last changed
    change_reason: str                   # Why was it changed?
    
    # Environment scoping
    environment: str                     # "all", "development", "staging", "production"
```

### 2.2 Critical Cost Control Feature Flags

| Flag Key | Type | Default | Cost Category | Est. Daily Cost | Description |
|----------|------|---------|---------------|-----------------|-------------|
| `ENABLE_REAL_TIME_WEBSOCKET` | boolean | false | network | $5-20 | WebSocket connections for live updates |
| `ENABLE_ML_PREDICTIONS` | boolean | true | compute | $10-50 | ML model inference for predictions |
| `ENABLE_SOCIAL_SCRAPING` | boolean | true | api | $20-100 | Social media data collection |
| `ENABLE_BIGQUERY_STREAMING` | boolean | false | storage | $15-30 | Real-time BigQuery streaming inserts |
| `ENABLE_ADVANCED_ANALYTICS` | boolean | false | compute | $5-15 | Complex analytical queries |
| `ENABLE_GOLD_DATA` | boolean | true | api | $5-10 | Gold price data (GoldAPI, etc.) |
| `ENABLE_CRYPTO_DATA` | boolean | true | api | $5-10 | Crypto data (Binance API) |
| `CACHE_TTL_SECONDS` | integer | 300 | - | Saves $ | Cache duration for API responses |
| `PREDICTION_HORIZON_HOURS` | integer | 24 | compute | Varies | How far ahead to predict |
| `MAX_CONCURRENT_SCRAPERS` | integer | 3 | compute | Varies | Limit parallel scraping jobs |
| `BIGQUERY_QUERY_CACHE_HOURS` | integer | 1 | compute | Saves $ | Cache BigQuery results |

### 2.3 Feature Flag API Endpoints

```
# Admin Panel Feature Flag API
GET    /api/v1/admin/feature-flags              → List all flags
GET    /api/v1/admin/feature-flags/{key}        → Get specific flag
PUT    /api/v1/admin/feature-flags/{key}        → Update flag value
POST   /api/v1/admin/feature-flags/{key}/toggle → Quick toggle boolean
GET    /api/v1/admin/feature-flags/cost-impact  → Cost impact summary

# Public API (read-only for services)
GET    /api/v1/feature-flags                    → Get all enabled flags (cached)
GET    /api/v1/feature-flags/{key}              → Check specific flag
```

### 2.4 Feature Flag Integration Pattern

```python
# In microservices - Feature Flag Client
from sentilyze_core.feature_flags import FeatureFlagClient

ff_client = FeatureFlagClient()

# Check if feature is enabled
if ff_client.is_enabled("ENABLE_ML_PREDICTIONS"):
    predictions = ml_model.predict(data)
else:
    # Fallback: Use cached predictions or simple heuristic
    predictions = get_cached_predictions()

# Get integer value
max_scrapers = ff_client.get_int("MAX_CONCURRENT_SCRAPERS", default=3)

# Decorator for automatic feature gating
@feature_required("ENABLE_SOCIAL_SCRAPING")
async def scrape_social_media():
    # Only runs if feature is enabled
    pass
```

---

## 3. Cost Control Strategy

### 3.1 Cost Control Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    COST CONTROL HIERARCHY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: Feature Flags (Admin Panel)                           │
│  ├── Global on/off switches for expensive features              │
│  ├── Real-time cost impact visibility                           │
│  └── Immediate effect (no deployment needed)                    │
│                                                                  │
│  LAYER 2: Budget Alerts (Automated)                             │
│  ├── Daily spend monitoring                                     │
│  ├── Threshold alerts (50%, 75%, 90%, 100%)                     │
│  └── Auto-disable non-critical features at 90%                  │
│                                                                  │
│  LAYER 3: Service Quotas (Per-Service Limits)                   │
│  ├── Max requests per minute/hour/day                           │
│  ├── Concurrent connection limits                               │
│  └── Resource usage caps                                        │
│                                                                  │
│  LAYER 4: Infrastructure Tiering                                │
│  ├── Development: Minimal resources                             │
│  ├── Staging: Moderate resources                                │
│  └── Production: Scaled resources with limits                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Budget Tiers Configuration

```python
# Budget tiers with feature flag presets
BUDGET_TIERS = {
    "minimal": {
        "monthly_budget_usd": 50,
        "feature_flags": {
            "ENABLE_REAL_TIME_WEBSOCKET": False,
            "ENABLE_ML_PREDICTIONS": True,
            "ENABLE_SOCIAL_SCRAPING": False,  # Manual only
            "ENABLE_BIGQUERY_STREAMING": False,
            "ENABLE_ADVANCED_ANALYTICS": False,
            "CACHE_TTL_SECONDS": 600,
            "MAX_CONCURRENT_SCRAPERS": 1,
        }
    },
    "basic": {
        "monthly_budget_usd": 200,
        "feature_flags": {
            "ENABLE_REAL_TIME_WEBSOCKET": False,
            "ENABLE_ML_PREDICTIONS": True,
            "ENABLE_SOCIAL_SCRAPING": True,
            "ENABLE_BIGQUERY_STREAMING": False,
            "ENABLE_ADVANCED_ANALYTICS": False,
            "CACHE_TTL_SECONDS": 300,
            "MAX_CONCURRENT_SCRAPERS": 2,
        }
    },
    "standard": {
        "monthly_budget_usd": 500,
        "feature_flags": {
            "ENABLE_REAL_TIME_WEBSOCKET": True,
            "ENABLE_ML_PREDICTIONS": True,
            "ENABLE_SOCIAL_SCRAPING": True,
            "ENABLE_BIGQUERY_STREAMING": True,
            "ENABLE_ADVANCED_ANALYTICS": True,
            "CACHE_TTL_SECONDS": 180,
            "MAX_CONCURRENT_SCRAPERS": 5,
        }
    },
    "premium": {
        "monthly_budget_usd": 1000,
        "feature_flags": {
            "ENABLE_REAL_TIME_WEBSOCKET": True,
            "ENABLE_ML_PREDICTIONS": True,
            "ENABLE_SOCIAL_SCRAPING": True,
            "ENABLE_BIGQUERY_STREAMING": True,
            "ENABLE_ADVANCED_ANALYTICS": True,
            "CACHE_TTL_SECONDS": 60,
            "MAX_CONCURRENT_SCRAPERS": 10,
        }
    }
}
```

### 3.3 Cost Monitoring Dashboard (Admin Panel)

```
┌─────────────────────────────────────────────────────────────────┐
│                    COST MONITORING DASHBOARD                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CURRENT MONTH                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Spent: $245.50 / $500.00  [████████░░░░░░░░░░] 49%    │    │
│  │  Projected: $520 (104% of budget) ⚠️                   │    │
│  │  Daily Average: $8.15 | Days Remaining: 15             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  COST BY CATEGORY                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  API Calls      $120.50  ██████████████████ 49%        │    │
│  │  Compute        $85.00   ████████████░░░░░░ 35%        │    │
│  │  Storage        $25.00   ███░░░░░░░░░░░░░░░ 10%        │    │
│  │  Network        $15.00   ██░░░░░░░░░░░░░░░░  6%        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  TOP SERVICES BY COST                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. Social Scraping    $95.00   ⚠️ High                │    │
│  │  2. ML Predictions     $65.00                          │    │
│  │  3. BigQuery Queries   $45.00                          │    │
│  │  4. WebSocket Conn     $25.00                          │    │
│  │  5. Gold API           $15.50                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ACTIVE FEATURE FLAGS (Cost Impact)                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  [ON]  WebSocket       ~$25/day    [Toggle OFF]        │    │
│  │  [ON]  ML Predictions  ~$50/day    [Toggle OFF]        │    │
│  │  [ON]  Social Scraping ~$80/day    [Toggle OFF]        │    │
│  │  [OFF] BigQuery Stream  $0/day     [Toggle ON]         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Backend-Frontend Integration API Contracts

### 4.1 API Gateway Integration

```yaml
# API Gateway Routes for Website

# Public Marketing API (Cached, No Auth)
GET  /api/v1/public/stats           → Platform statistics (cached 5min)
GET  /api/v1/public/health          → System health status
GET  /api/v1/public/pricing         → Pricing tiers
GET  /api/v1/public/case-studies    → Case study summaries

# Dashboard API (Requires Auth)
GET  /api/v1/dashboard/overview     → Dashboard overview data
GET  /api/v1/dashboard/sentiment    → Sentiment analysis data
GET  /api/v1/dashboard/predictions  → Predictions & accuracy
GET  /api/v1/dashboard/market       → Market data & charts
GET  /api/v1/dashboard/sources      → Data source status

# Gold Dashboard Specific (/altin)
GET  /api/v1/gold/price             → Current gold price (multi-currency)
GET  /api/v1/gold/history           → Price history
GET  /api/v1/gold/sentiment         → Gold sentiment analysis
GET  /api/v1/gold/technical         → Technical indicators
GET  /api/v1/gold/correlation       → Correlation analysis
GET  /api/v1/gold/predictions       → Gold price predictions

# Admin API (Requires Admin Auth)
GET  /api/v1/admin/feature-flags    → Feature flag management
PUT  /api/v1/admin/feature-flags    → Update feature flags
GET  /api/v1/admin/costs            → Cost tracking
GET  /api/v1/admin/budget           → Budget configuration
GET  /api/v1/admin/users            → User management
GET  /api/v1/admin/audit-logs       → Audit logs
```

### 4.2 Data Contracts

```typescript
// Dashboard Overview Response
interface DashboardOverview {
  assets: {
    symbol: string;
    name: string;
    currentPrice: number;
    priceChange24h: number;
    sentimentScore: number;
    sentimentChange: number;
  }[];
  sentimentTimeline: {
    date: string;
    btc: number;
    eth: number;
    xau: number;
  }[];
  activePredictions: {
    asset: string;
    direction: 'UP' | 'DOWN';
    confidence: number;
    predictedChange: number;
    status: 'pending' | 'correct' | 'incorrect';
  }[];
  lastUpdated: string;
}

// Gold Dashboard Response
interface GoldDashboardData {
  price: {
    usd: number;
    eur: number;
    try: number;
    change24h: number;
  };
  sentiment: {
    score: number;
    label: 'positive' | 'neutral' | 'negative';
    confidence: number;
    distribution: {
      positive: number;
      neutral: number;
      negative: number;
    };
  };
  technicalIndicators: {
    rsi: number;
    macd: number;
    bollingerBands: {
      upper: number;
      middle: number;
      lower: number;
    };
    ma20: number;
  };
  predictions: {
    horizon: string;
    predictedPrice: number;
    confidence: number;
    direction: 'UP' | 'DOWN';
  }[];
  correlations: {
    usdStrength: number;
    treasuryYields: number;
    btc: number;
    sp500: number;
  };
}

// Feature Flag Response
interface FeatureFlag {
  key: string;
  name: string;
  description: string;
  category: 'cost_control' | 'feature' | 'experimental';
  valueType: 'boolean' | 'integer' | 'string' | 'json';
  currentValue: any;
  defaultValue: any;
  isEnabled: boolean;
  estimatedDailyCostUsd: number;
  costCategory: string;
  affectedServices: string[];
  updatedAt: string;
  updatedBy: string;
  changeReason: string;
}
```

### 4.3 WebSocket Contracts (Optional - Feature Flag Controlled)

```typescript
// WebSocket Events (if ENABLE_REAL_TIME_WEBSOCKET is true)

// Client → Server
{
  "action": "subscribe",
  "channels": ["gold-price", "gold-sentiment", "predictions"]
}

// Server → Client
{
  "channel": "gold-price",
  "data": {
    "symbol": "XAUUSD",
    "price": 2043.50,
    "timestamp": "2026-01-31T21:54:00Z"
  }
}

{
  "channel": "gold-sentiment",
  "data": {
    "score": 0.52,
    "volume": 1234,
    "timestamp": "2026-01-31T21:54:00Z"
  }
}
```

---

## 5. Gold Dashboard (/altin) Design Specification

### 5.1 Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  SENTILYZE                                    [User] [Logout]   │
│  Gold Analysis Dashboard (XAU/USD)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Overview] [Sentiment] [Predictions] [Market] [Sources]       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  QUICK STATS ROW                                                 │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │  XAU/USD     │  Sentiment   │  Prediction  │  Data Sources│  │
│  │  $2,043.50   │  😊 +0.52    │  ▲ +0.9%     │     12       │  │
│  │  ▲ +0.8%     │  Positive    │  68% conf    │  Active      │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                  │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│  │   SENTIMENT TIMELINE     │  │    ANALYSIS BOX              │ │
│  │   [Line Chart - 7 days]  │  │                              │ │
│  │                          │  │  Advanced correlation        │ │
│  │   Sentiment vs Price     │  │  analysis and detailed       │ │
│  │   lag visualization      │  │  market insights...          │ │
│  │                          │  │                              │ │
│  │                          │  │  [View Full Analysis →]      │ │
│  └──────────────────────────┘  └──────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           ACTIVE PREDICTIONS (24h Horizon)                 │ │
│  │  ┌─────────┬──────────┬────────────┬──────────┬──────────┐ │ │
│  │  │ Asset   │ Direction│ Confidence │ Change   │ Status   │ │ │
│  │  ├─────────┼──────────┼────────────┼──────────┼──────────┤ │ │
│  │  │ XAU/USD │  ▲ UP    │    68%     │  +0.9%   │ ⏳ Pend..│ │ │
│  │  └─────────┴──────────┴────────────┴──────────┴──────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Tab: Sentiment

```
┌─────────────────────────────────────────────────────────────────┐
│  FILTERS: [Asset: XAU ▼] [Period: 7 Days ▼] [Source: All ▼]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────┐  ┌────────────────────────────┐ │
│  │     SENTIMENT GAUGE        │  │    SENTIMENT DISTRIBUTION  │ │
│  │                            │  │                            │ │
│  │        ╔══════════╗        │  │    Positive (65%)          │ │
│  │        ║  +0.52   ║        │  │  ╔══════════════════╗      │ │
│  │        ║  😊      ║        │  │  ║     65%          ║      │ │
│  │        ║ Positive ║        │  │  ╚══════════════════╝      │ │
│  │        ╚══════════╝        │  │  Neutral (25%)  Neg (10%)  │ │
│  │                            │  │  ╔════════╗    ╔════╗      │ │
│  │   Confidence: 87%          │  │  ║  25%   ║    ║10% ║      │ │
│  │                            │  │  ╚════════╝    ╚════╝      │ │
│  └────────────────────────────┘  └────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────┐  ┌────────────────────────────┐ │
│  │     EMOTION BREAKDOWN      │  │    TRENDING KEYWORDS       │ │
│  │                            │  │                            │ │
│  │  Joy         ████████ 78%  │  │  inflation  ETF  rally     │ │
│  │  Trust       ██████   65%  │  │  Fed  rates  gold  safe    │ │
│  │  Fear        ███      28%  │  │  haven  dollar  bullion    │ │
│  │  Anticipation █████   55%  │  │  reserve  central  bank    │ │
│  │  Anger       ██       18%  │  │                            │ │
│  │  Sadness     ██       15%  │  │                            │ │
│  └────────────────────────────┘  └────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Tab: Market

```
┌─────────────────────────────────────────────────────────────────┐
│  MULTI-CURRENCY PRICES                                           │
│  ┌─────────────┬─────────────┬─────────────┐                    │
│  │  USD        │  EUR        │  TRY        │                    │
│  │  $2,043.50  │  €1,889.20  │  ₺65,320    │                    │
│  │  ▲ +0.8%    │  ▲ +0.6%    │  ▲ +1.2%    │                    │
│  └─────────────┴─────────────┴─────────────┘                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PRICE CHART (30 Days)                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │    $2,100 ┤                           ╱─╲                 │ │
│  │           │                       ╱───   ╲──╲              │ │
│  │    $2,080 ┤    BB Upper ─ ─ ─ ─╱─ ─ ─ ─ ─ ─ ─╲─ ─ ─      │ │
│  │           │               ╱───╱                ╲───        │ │
│  │    $2,060 ┤    MA20 ─────╱                                 │ │
│  │           │           ╱───                                 │ │
│  │    $2,040 ┤    BB ───╱─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─       │ │
│  │           │       ╱───                                     │ │
│  │    $2,020 ┤   ╱───                                         │ │
│  │           └───┬────┬────┬────┬────┬────                    │ │
│  │              1w   2w   3w   4w   Now                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  TECHNICAL INDICATORS                                            │
│  ┌────────────────────────────┐  ┌────────────────────────────┐ │
│  │  RSI (14):     58.3  Neutral│  │  CORRELATIONS              │ │
│  │  MACD:        +12.5  Bullish│  │                            │ │
│  │  Bollinger:                 │  │  USD Strength   -0.68      │ │
│  │    Upper:  $2,080           │  │  Treasury Ylds  -0.42      │ │
│  │    Middle: $2,050           │  │  BTC            +0.35      │ │
│  │    Lower:  $2,020           │  │  S&P 500        -0.28      │ │
│  │  MA20:      $2,035          │  │                            │ │
│  └────────────────────────────┘  └────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Admin Panel Feature Flags UI Design

### 6.1 Feature Flags Management Page

```
┌─────────────────────────────────────────────────────────────────┐
│  SENTILYZE ADMIN                                    [Admin] ▼   │
├─────────────────────────────────────────────────────────────────┤
│  [Dashboard] [Users] [API Keys] [FEATURE FLAGS] [Budget] [Logs] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FEATURE FLAGS MANAGEMENT                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Filter: [All ▼]  Search: [____________]  [+ New Flag]     │ │
│  │                                                            │ │
│  │  ⚠️ COST CONTROL FLAGS (High Impact)                       │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                                                            │ │
│  │  🟢 ENABLE_ML_PREDICTIONS                                  │ │
│  │     ML model predictions for price forecasting              │ │
│  │     Est. cost: ~$50/day | Category: Compute               │ │
│  │     [Toggle: ON]  [Edit]  [View Logs]                     │ │
│  │                                                            │ │
│  │  🟡 ENABLE_SOCIAL_SCRAPING                                 │ │
│  │     Social media data collection (Twitter, Reddit)        │ │
│  │     Est. cost: ~$80/day | Category: API                   │ │
│  │     ⚠️ High cost - consider reducing frequency            │ │
│  │     [Toggle: ON]  [Edit]  [View Logs]                     │ │
│  │                                                            │ │
│  │  🔴 ENABLE_REAL_TIME_WEBSOCKET                             │ │
│  │     Real-time WebSocket connections for live updates      │ │
│  │     Est. cost: ~$25/day | Category: Network               │ │
│  │     [Toggle: OFF]  [Edit]  [View Logs]                    │ │
│  │                                                            │ │
│  │  🟢 ENABLE_GOLD_DATA                                       │ │
│  │     Gold price data from GoldAPI and other sources        │ │
│  │     Est. cost: ~$8/day | Category: API                    │ │
│  │     [Toggle: ON]  [Edit]  [View Logs]                     │ │
│  │                                                            │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │  ⚙️ CONFIGURATION FLAGS                                    │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                                                            │ │
│  │  CACHE_TTL_SECONDS                                         │ │
│  │     Cache duration for API responses                      │ │
│  │     Current: 300 seconds (5 minutes)                      │ │
│  │     [Edit Value]                                          │ │
│  │                                                            │ │
│  │  MAX_CONCURRENT_SCRAPERS                                   │ │
│  │     Maximum parallel scraping jobs                        │ │
│  │     Current: 3                                            │ │
│  │     [Edit Value]                                          │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  TOTAL ESTIMATED DAILY COST: $163 (with current settings)       │
│  PROJECTED MONTHLY: ~$4,890                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Feature Flag Edit Modal

```
┌─────────────────────────────────────────────────────────────┐
│  Edit Feature Flag                              [X]         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Flag Key: ENABLE_SOCIAL_SCRAPING                           │
│  Name: Social Media Scraping                                │
│  Description:                                               │
│  [Collect data from Twitter, Reddit, and other social     ] │
│  [media platforms for sentiment analysis                  ] │
│                                                              │
│  Category: [Cost Control ▼]                                 │
│  Value Type: [Boolean ▼]                                    │
│                                                              │
│  Current Value: [☑️ Enabled]                                 │
│                                                              │
│  Cost Impact:                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Estimated Daily Cost: $80.00                       │   │
│  │  Cost Category: API                                 │   │
│  │  Affected Services: ingestion, sentiment-processor  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Change Reason (required):                                  │
│  [______________________________________________________]  │
│                                                              │
│  [Cancel]                              [Save Changes]       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Tech Stack Recommendation

### 7.1 Frontend Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| Framework | Next.js 14 (App Router) | SSR for SEO, static export option, React 18 |
| Language | TypeScript | Type safety, better DX |
| Styling | Tailwind CSS | Rapid development, consistent design |
| UI Components | shadcn/ui | Accessible, customizable components |
| Charts | Recharts + Lightweight-charts | Interactive charts, financial data support |
| State | Zustand | Simple, effective state management |
| Data Fetching | TanStack Query | Caching, optimistic updates |
| Auth | NextAuth.js | Easy integration with FastAPI JWT |
| Icons | Lucide React | Clean, consistent iconography |

### 7.2 Backend Integration

| Component | Technology | Notes |
|-----------|------------|-------|
| API Gateway | FastAPI (existing) | Reuse existing infrastructure |
| Feature Flags | PostgreSQL + Redis Cache | Fast lookups, persistent storage |
| Admin Panel | FastAPI + Jinja2 (existing) | Extend existing admin-panel service |
| Auth | JWT (existing) | Integrate with existing auth system |

### 7.3 Hosting & Deployment

| Component | Provider | Cost Estimate |
|-----------|----------|---------------|
| Marketing Website | Vercel (Free/Hobby) | $0-20/month |
| Dashboard (Static) | Vercel | $0-20/month |
| Admin Panel | Cloud Run (existing) | Part of existing infra |
| API Gateway | Cloud Run (existing) | Part of existing infra |
| Feature Flags DB | PostgreSQL (existing) | Part of existing infra |
| CDN | Vercel Edge | Included |

### 7.4 Cost-Effective Architecture Decisions

1. **Static Site Generation (SSG) for Marketing Pages**
   - Pre-render all marketing pages at build time
   - Zero server costs for public pages
   - ISR (Incremental Static Regeneration) for blog updates

2. **Client-Side Data Fetching for Dashboards**
   - Dashboards fetch data from API Gateway on client
   - No SSR costs for authenticated pages
   - Caching via TanStack Query

3. **Feature Flag Caching**
   - Redis cache for feature flags (5-min TTL)
   - Reduces database queries
   - Fast feature checks in microservices

4. **Conditional WebSocket Usage**
   - WebSocket only when `ENABLE_REAL_TIME_WEBSOCKET` is true
   - Fallback to polling for cost-sensitive tiers
   - Connection limits enforced

5. **Image Optimization**
   - Next.js Image component with Vercel optimization
   - WebP format, responsive sizes
   - Reduces bandwidth costs

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up Next.js project with TypeScript and Tailwind
- [ ] Configure shadcn/ui components
- [ ] Create base layout and navigation
- [ ] Set up API client for FastAPI integration
- [ ] Implement authentication flow (JWT)

### Phase 2: Marketing Pages (Week 2)
- [ ] Landing page (`/`) with lag analysis focus
- [ ] About page (`/about`)
- [ ] Product page (`/product`)
- [ ] How It Works page (`/how-it-works`)
- [ ] Pricing page (`/pricing`)
- [ ] Contact page (`/contact`)

### Phase 3: Feature Flag System (Week 3)
- [ ] Create feature flag database schema
- [ ] Implement feature flag API endpoints
- [ ] Create feature flag client library
- [ ] Add feature flag checks to microservices
- [ ] Build admin panel feature flags UI

### Phase 4: Gold Dashboard (Week 4)
- [ ] Dashboard layout with tabs
- [ ] Overview tab implementation
- [ ] Sentiment tab with charts
- [ ] Predictions tab
- [ ] Market tab with price charts
- [ ] Sources tab
- [ ] Analysis box linking to analysis page

### Phase 5: Admin Panel Integration (Week 5)
- [ ] Extend existing admin-panel with feature flags
- [ ] Cost monitoring dashboard
- [ ] Budget management UI
- [ ] User management
- [ ] Audit logs viewer

### Phase 6: Polish & Optimization (Week 6)
- [ ] Performance optimization
- [ ] SEO optimization
- [ ] Mobile responsiveness
- [ ] Error handling and loading states
- [ ] Documentation
- [ ] Deploy to Vercel

---

## 9. Key Implementation Notes

### 9.1 Feature Flag Integration Points

```python
# Add to existing microservices

# 1. Ingestion Service
if feature_flags.is_enabled("ENABLE_SOCIAL_SCRAPING"):
    await scrape_social_media()

# 2. Prediction Engine
if feature_flags.is_enabled("ENABLE_ML_PREDICTIONS"):
    predictions = ml_model.predict(data)
else:
    predictions = get_cached_predictions()

# 3. API Gateway
if feature_flags.is_enabled("ENABLE_REAL_TIME_WEBSOCKET"):
    enable_websocket_routes()

# 4. Analytics Engine
if feature_flags.is_enabled("ENABLE_ADVANCED_ANALYTICS"):
    run_complex_analytics()
```

### 9.2 Admin Panel Hidden Access

```python
# In main website - middleware or config
# Admin panel is at /admin but NOT linked from anywhere
# Access requires:
# 1. Knowing the URL (/admin)
# 2. Valid admin credentials
# 3. Admin role permission

# robots.txt - don't index admin
User-agent: *
Disallow: /admin/
Allow: /
```

### 9.3 Cost Tracking Integration

```python
# Track costs when features are used
from sentilyze_core.cost_tracking import track_cost

async def scrape_twitter():
    if not feature_flags.is_enabled("ENABLE_SOCIAL_SCRAPING"):
        return
    
    # Track API call cost
    track_cost(
        service="twitter_scraper",
        category="api",
        cost_type="api_call",
        estimated_cost=0.01  # $0.01 per call
    )
    
    # Perform scraping
    await perform_scrape()
```

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Page Load Time (Marketing) | < 2s |
| Page Load Time (Dashboard) | < 3s |
| API Response Time | < 500ms |
| Feature Flag Propagation | < 5s |
| Monthly Infrastructure Cost | <$500 (minimal tier) |
| Google Lighthouse Score | > 90 |
| SEO Score | > 90 |

---

## Appendix A: API Endpoint Summary

### Public Endpoints (No Auth)
- `GET /api/v1/public/health`
- `GET /api/v1/public/stats`
- `GET /api/v1/public/pricing`

### Dashboard Endpoints (Auth Required)
- `GET /api/v1/dashboard/overview`
- `GET /api/v1/dashboard/sentiment/{symbol}`
- `GET /api/v1/dashboard/predictions/{symbol}`
- `GET /api/v1/dashboard/market/{symbol}`
- `GET /api/v1/dashboard/sources`

### Gold-Specific Endpoints
- `GET /api/v1/gold/price`
- `GET /api/v1/gold/history`
- `GET /api/v1/gold/sentiment`
- `GET /api/v1/gold/technical`
- `GET /api/v1/gold/predictions`

### Admin Endpoints (Admin Auth Required)
- `GET /api/v1/admin/feature-flags`
- `PUT /api/v1/admin/feature-flags/{key}`
- `GET /api/v1/admin/costs`
- `GET /api/v1/admin/budget`
- `GET /api/v1/admin/users`

---

## Appendix B: Database Schema Additions

### Feature Flags Table
```sql
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    value_type VARCHAR(20) NOT NULL,
    default_value JSONB NOT NULL,
    current_value JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    requires_restart BOOLEAN DEFAULT false,
    affected_services JSONB DEFAULT '[]',
    estimated_daily_cost_usd NUMERIC(10, 6),
    cost_category VARCHAR(50),
    environment VARCHAR(50) DEFAULT 'all',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES admin_users(id),
    change_reason TEXT
);

CREATE INDEX idx_feature_flags_key ON feature_flags(key);
CREATE INDEX idx_feature_flags_category ON feature_flags(category);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled);
```

---

*Document Version: 1.0*
*Created: 2026-01-31*
*For: Sentilyze Crypto Lag Sentiment Analysis Platform*
