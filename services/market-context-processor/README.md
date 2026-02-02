# Market Context Processor

Market analysis service providing regime detection, anomaly detection, and correlation analysis for crypto and gold markets.

## Overview

This service analyzes market data to detect market regimes (bull/bear/neutral), identify anomalies in price/volume/sentiment, and calculate correlations between assets including Granger causality testing.

## Features

- **Regime Detection**: Identify market regimes (bull/bear/neutral) with confidence scores
- **Anomaly Detection**: Detect price, sentiment, and volume anomalies with severity levels
- **Correlation Analysis**: Calculate asset correlations with lag analysis
- **Granger Causality**: Test if sentiment predicts price movements
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Moving Averages
- **Pub/Sub Integration**: Event-driven processing via push subscriptions
- **BigQuery Integration**: Market context data storage

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Market Context Processor                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Analysis Endpoints                                          │
│  ├─→ /analyze/regime      - Market regime detection          │
│  ├─→ /analyze/anomalies   - Anomaly detection                │
│  ├─→ /analyze/correlation - Asset correlation                │
│  └─→ /analyze/granger     - Granger causality test           │
│                                                              │
│  Pub/Sub Integration                                         │
│  └─→ /pubsub-push/processed-sentiment                       │
│       └─→ Extract market context from sentiment              │
│       └─→ Publish to market-context topic                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/ready` | GET | Readiness check with dependency validation |

**Health Check Response:**
```json
{
  "status": "healthy",
  "service": "market-context-processor",
  "version": "3.0.0"
}
```

### Analysis Endpoints

#### Regime Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/regime` | POST | Detect market regime from price data |

**Request:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "prices": [45000, 45200, 45100, ...],  // Min 50 data points
  "volumes": [1000000, 1200000, ...]     // Optional
}
```

**Response:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "regime": "bull",
  "trend_direction": "up",
  "volatility_regime": "normal",
  "confidence": 0.82,
  "rsi_14": 65.4,
  "sma_50": 44500,
  "sma_200": 42000,
  "ema_20": 45200,
  "price": 46800,
  "support_level": 44000,
  "resistance_level": 48000,
  "trend_strength": 0.75,
  "volume_trend": "increasing",
  "timestamp": "2026-01-31T12:00:00Z"
}
```

#### Anomaly Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/anomalies` | POST | Detect anomalies in market data |

**Request:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "prices": [45000, 45200, 48000, ...],  // Min 20 data points
  "sentiments": [0.2, 0.3, 0.8, ...],    // Optional
  "volumes": [1000000, 1200000, ...],    // Optional
  "support_level": 44000,                // Optional
  "resistance_level": 48000              // Optional
}
```

**Response:**
```json
{
  "anomalies": [
    {
      "anomaly_type": "price_breakout",
      "severity": "high",
      "symbol": "BTC",
      "market_type": "crypto",
      "timestamp": "2026-01-31T12:00:00Z",
      "description": "Price broke above resistance at $48,000",
      "price_at_detection": 48100,
      "price_change_percent": 6.9,
      "volume_ratio": 1.8,
      "z_score": 2.5,
      "recommendation": "Monitor for trend continuation"
    }
  ],
  "total_anomalies": 1,
  "critical_count": 0,
  "high_count": 1,
  "medium_count": 0,
  "low_count": 0
}
```

#### Correlation Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/correlation` | POST | Calculate correlation between two assets |

**Request:**
```json
{
  "primary_symbol": "BTC",
  "secondary_symbol": "ETH",
  "primary_prices": [45000, 45200, ...],   // Min 30 points
  "secondary_prices": [3000, 3050, ...],   // Same length
  "market_type": "crypto",
  "period_days": 30,
  "calculate_lag": true
}
```

**Response:**
```json
{
  "primary_symbol": "BTC",
  "secondary_symbol": "ETH",
  "market_type": "crypto",
  "correlation": 0.85,
  "correlation_strength": "strong",
  "period_days": 30,
  "sample_size": 720,
  "interpretation": "Strong positive correlation. Assets tend to move together.",
  "lag_analysis": {
    "optimal_lag_hours": 2,
    "lag_correlation": 0.87,
    "lead_lag_relationship": "BTC leads ETH by ~2 hours"
  },
  "rolling_correlations": [...],
  "timestamp": "2026-01-31T12:00:00Z"
}
```

#### Granger Causality

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/granger` | POST | Test if sentiment predicts price movements |

**Request:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "prices": [45000, 45200, ...],      // Min 30 points
  "sentiments": [0.2, 0.3, ...],      // Same length
  "max_lag_hours": 24
}
```

**Response:**
```json
{
  "cause_variable": "sentiment",
  "effect_variable": "price",
  "market_type": "crypto",
  "lag_hours": 6,
  "f_statistic": 12.5,
  "p_value": 0.002,
  "is_causal": true,
  "interpretation": "Sentiment Granger-causes price with 6-hour lag (p<0.05). Changes in sentiment precede price movements.",
  "timestamp": "2026-01-31T12:00:00Z"
}
```

### Pub/Sub Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pubsub-push/processed-sentiment` | POST | Pub/Sub push subscription endpoint |

Processes messages from Pub/Sub `processed-sentiment` topic and publishes market context events.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_REGIME_DETECTION` | `true` | Enable regime detection |
| `ENABLE_ANOMALY_DETECTION` | `true` | Enable anomaly detection |
| `ENABLE_CORRELATION_ANALYSIS` | `true` | Enable correlation analysis |
| `CORS_ORIGINS` | `https://sentilyze.live,...` | Allowed CORS origins |

## Running Locally

```bash
# Install dependencies
cd services/market-context-processor
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload --port 8083

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8083
```

## Docker

```bash
# Build from repo root
docker build -f services/market-context-processor/Dockerfile -t market-context-processor:3.0.0 .

# Run
docker run -p 8083:8083 market-context-processor:3.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8083/health

# Regime detection
curl -X POST http://localhost:8083/analyze/regime \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "market_type": "crypto",
    "prices": [45000, 45200, 45100, 45300, ...]  // 50+ prices
  }'

# Anomaly detection
curl -X POST http://localhost:8083/analyze/anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "prices": [45000, 45200, 48000, ...],  // 20+ prices
    "support_level": 44000,
    "resistance_level": 48000
  }'

# Correlation analysis
curl -X POST http://localhost:8083/analyze/correlation \
  -H "Content-Type: application/json" \
  -d '{
    "primary_symbol": "BTC",
    "secondary_symbol": "ETH",
    "primary_prices": [45000, 45200, ...],  // 30+ prices
    "secondary_prices": [3000, 3050, ...]   // Same length
  }'

# Granger causality
curl -X POST http://localhost:8083/analyze/granger \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "prices": [45000, 45200, ...],  // 30+ prices
    "sentiments": [0.2, 0.3, ...],   // Same length
    "max_lag_hours": 24
  }'
```

## Analysis Types

### Regime Detection
Detects market regimes using:
- RSI (Relative Strength Index)
- Moving averages (SMA 50/200, EMA 20)
- Trend direction and strength
- Volatility regime
- Support/resistance levels

### Anomaly Detection
Detects various anomaly types:
- **Price breakout**: Above resistance or below support
- **Volume spike**: Unusual trading volume
- **Sentiment divergence**: Sentiment-price mismatch
- **Z-score outliers**: Statistical anomalies

Severity levels: `critical`, `high`, `medium`, `low`

### Correlation Analysis
Calculates:
- Pearson correlation coefficient
- Correlation strength interpretation
- Optimal lag analysis
- Rolling correlations over time

### Granger Causality
Tests:
- Statistical causality between sentiment and price
- Optimal lag hours
- F-statistic and p-value
- Causality interpretation

## Project Structure

```
services/market-context-processor/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and enums
│   ├── analyzer.py          # RegimeDetector and AnomalyDetector
│   ├── correlation.py       # CorrelationAnalyzer
│   ├── models.py            # Data models
│   └── publisher.py         # Pub/Sub publishing
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Integration

### Upstream (Input)
- **Sentiment Processor**: Publishes processed sentiment to `processed-sentiment` topic
- **Direct API**: Price/volume data from clients

### Downstream (Output)
- **BigQuery**: Stores market context data
- **Pub/Sub**: Publishes to `market-context` topic
- **Prediction Engine**: Uses market context for predictions

## License

MIT License - Sentilyze Team
