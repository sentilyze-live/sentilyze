# Analytics Engine

Statistical analysis, aggregation, and insights generation service for market data.

## Overview

This service provides analytics aggregation, sentiment trend analysis, market comparison, and correlation insights. It materializes aggregated metrics into BigQuery for dashboard visualization and reporting.

## Features

- **Analytics Materialization**: Aggregate and store metrics in BigQuery
- **Sentiment Trends**: Track sentiment changes over time
- **Market Comparison**: Compare sentiment across multiple symbols
- **Correlation Analysis**: Sentiment-price correlation insights
- **BigQuery Integration**: Analytics data storage and querying
- **Time Window Analysis**: Configurable time windows (1h to 7 days)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Analytics Engine                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Analytics Jobs                                              │
│  └─→ /jobs/materialize-analytics                            │
│       └─→ Compute metrics for time window                    │
│       └─→ Write to BigQuery analytics table                  │
│                                                              │
│  Sentiment Analysis                                          │
│  ├─→ /sentiment/trend/{symbol}   - Sentiment trend           │
│  └─→ /sentiment/compare          - Multi-symbol comparison   │
│                                                              │
│  Correlation                                                 │
│  └─→ /correlation/{symbol}       - Sentiment-price correlation│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/ready` | GET | Readiness check with dependency validation |
| `/status` | GET | Service status and configuration |

**Health Check Response:**
```json
{
  "status": "healthy",
  "service": "analytics-engine",
  "version": "3.0.0"
}
```

**Status Response:**
```json
{
  "service": "analytics-engine",
  "materialization_enabled": true,
  "correlation_enabled": true,
  "granger_enabled": false,
  "aggregator_ready": true
}
```

### Analytics Jobs

#### Materialize Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs/materialize-analytics` | POST | Materialize aggregated metrics into BigQuery |

**Query Parameters:**
- `hours` (int, default: 24): Window size in hours (1-168)
- `also_last_1h` (bool, default: true): Also materialize last 1 hour

**Response:**
```json
{
  "status": "ok",
  "windows": [
    {
      "windowHours": 1.0,
      "metrics": {
        "sentiment_avg": 0.45,
        "sentiment_volume": 1250,
        "symbol": "BTC",
        ...
      },
      "rowsWritten": 1
    },
    {
      "windowHours": 24.0,
      "metrics": {
        "sentiment_avg": 0.42,
        "sentiment_volume": 28400,
        "symbol": "BTC",
        ...
      },
      "rowsWritten": 1
    }
  ],
  "totalRowsWritten": 2
}
```

### Sentiment Analysis

#### Sentiment Trend

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sentiment/trend/{symbol}` | GET | Get sentiment trend for a symbol |

**Query Parameters:**
- `days` (int, default: 7): Number of days (1-90)

**Response:**
```json
{
  "symbol": "BTC",
  "days": 7,
  "trend": [
    {
      "date": "2026-01-25",
      "avg_sentiment": 0.35,
      "volume": 3200,
      "positive_ratio": 0.65
    },
    {
      "date": "2026-01-26",
      "avg_sentiment": 0.42,
      "volume": 4100,
      "positive_ratio": 0.72
    }
    // ... more days
  ],
  "generated_at": "2026-01-31T12:00:00Z"
}
```

#### Compare Sentiment

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sentiment/compare` | GET | Compare sentiment across multiple symbols |

**Query Parameters:**
- `symbols` (string, required): Comma-separated list of symbols (e.g., "BTC,ETH,XAU")
- `days` (int, default: 7): Number of days (1-30)

**Response:**
```json
{
  "symbols": ["BTC", "ETH", "XAU"],
  "days": 7,
  "comparison": {
    "BTC": {
      "avg_sentiment": 0.45,
      "total_volume": 28400,
      "positive_ratio": 0.68
    },
    "ETH": {
      "avg_sentiment": 0.38,
      "total_volume": 18200,
      "positive_ratio": 0.61
    },
    "XAU": {
      "avg_sentiment": 0.52,
      "total_volume": 9500,
      "positive_ratio": 0.74
    }
  },
  "leader": "XAU",
  "laggard": "ETH",
  "generated_at": "2026-01-31T12:00:00Z"
}
```

### Correlation

#### Sentiment-Price Correlation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/correlation/{symbol}` | GET | Get sentiment-price correlation (placeholder) |

**Query Parameters:**
- `lag` (int, default: 6): Lag in hours (0-48)
- `days` (int, default: 30): Days of data (7-365)

**Response:**
```json
{
  "symbol": "BTC",
  "lag_hours": 6,
  "correlation": 0.65,
  "p_value": 0.001,
  "significant": true,
  "note": "Full correlation analysis requires price data integration"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_MATERIALIZATION` | `true` | Enable analytics materialization |
| `ENABLE_CORRELATION_ANALYSIS` | `true` | Enable correlation analysis |
| `ENABLE_GRANGER_CAUSALITY` | `false` | Enable Granger causality testing |
| `CORS_ORIGINS` | `https://sentilyze.live,...` | Allowed CORS origins |

## Running Locally

```bash
# Install dependencies
cd services/analytics-engine
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload --port 8086

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8086
```

## Docker

```bash
# Build from repo root
docker build -f services/analytics-engine/Dockerfile -t analytics-engine:3.0.0 .

# Run
docker run -p 8086:8086 analytics-engine:3.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8086/health

# Materialize analytics
curl -X POST "http://localhost:8086/jobs/materialize-analytics?hours=24&also_last_1h=true"

# Get sentiment trend
curl "http://localhost:8086/sentiment/trend/BTC?days=7"

# Compare sentiment
curl "http://localhost:8086/sentiment/compare?symbols=BTC,ETH,XAU&days=7"

# Get correlation
curl "http://localhost:8086/correlation/BTC?lag=6&days=30"
```

## Materialization Process

```
┌──────────────────────────────────────────────────────────────┐
│                 Analytics Materialization                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Window Definition                                         │
│     └─→ Define time window (e.g., last 24 hours)              │
│                                                               │
│  2. Metrics Computation                                       │
│     ├─→ Aggregate sentiment scores                            │
│     ├─→ Count total events                                    │
│     ├─→ Calculate positive/negative ratios                    │
│     ├─→ Compute volume metrics                                │
│     └─→ Determine trend direction                             │
│                                                               │
│  3. BigQuery Storage                                          │
│     └─→ Insert aggregated metrics into analytics table        │
│                                                               │
│  4. Response                                                  │
│     └─→ Return metrics and row count                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
services/analytics-engine/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   └── aggregator.py        # AnalyticsAggregator
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Integration

### Upstream (Input)
- **BigQuery**: Reads processed events from Silver layer
- **Manual**: Direct API calls for ad-hoc analysis

### Downstream (Output)
- **BigQuery**: Stores materialized analytics
- **Dashboard**: Frontend visualizations
- **Reports**: Scheduled analytics reports

## Analytics Metrics

### Computed Metrics
- **avg_sentiment**: Average sentiment score (-1 to 1)
- **sentiment_volume**: Total number of events
- **positive_ratio**: Percentage of positive events
- **negative_ratio**: Percentage of negative events
- **neutral_ratio**: Percentage of neutral events
- **confidence_avg**: Average confidence score
- **trend_direction**: Increasing/Decreasing/Stable

### Time Windows
- **1 hour**: Real-time monitoring
- **24 hours**: Daily analytics
- **7 days**: Weekly trends

## License

MIT License - Sentilyze Team
