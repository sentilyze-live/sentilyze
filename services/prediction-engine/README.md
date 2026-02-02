# Prediction Engine

Price prediction service with technical analysis and ML for crypto and gold markets.

## Overview

This service generates price predictions using technical indicators and machine learning models. It supports multiple prediction timeframes and publishes predictions for downstream tracking.

## Features

- **Multi-Timeframe Predictions**: 30m, 1h, 3h, 6h prediction windows
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Moving Averages
- **ML Predictions**: Optional ML model integration
- **Batch Predictions**: Generate predictions for all timeframes at once
- **Confidence Scoring**: Confidence levels (low/medium/high) with reasoning
- **Pub/Sub Integration**: Event-driven prediction generation
- **BigQuery Integration**: Prediction storage for tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Prediction Engine                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Prediction Endpoints                                        │
│  ├─→ /predict            - Single timeframe prediction       │
│  └─→ /predict/batch      - All timeframes batch prediction   │
│                                                              │
│  Pub/Sub Integration                                         │
│  └─→ /pubsub-push/market-context                            │
│       └─→ Generate predictions from market context           │
│       └─→ Publish to predictions topic                       │
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
  "service": "prediction-engine",
  "version": "3.0.0"
}
```

**Status Response:**
```json
{
  "service": "prediction-engine",
  "ml_enabled": true,
  "technical_enabled": true,
  "crypto_enabled": true,
  "gold_enabled": true,
  "engine_ready": true
}
```

### Predictions

#### Single Prediction

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Generate price prediction for a single timeframe |

**Request:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "current_price": 46800.50,
  "prices": [45000, 45200, 45100, ...],  // Min 50 data points
  "sentiment_score": 0.65,
  "prediction_type": "1h"  // Options: 30m, 1h, 3h, 6h
}
```

**Response:**
```json
{
  "prediction_id": "uuid",
  "symbol": "BTC",
  "market_type": "crypto",
  "prediction_type": "1h",
  "current_price": 46800.50,
  "predicted_price": 47250.00,
  "predicted_direction": "UP",
  "confidence_score": 75,
  "confidence_level": "MEDIUM",
  "technical_indicators": {
    "rsi_14": 62.5,
    "macd": 150.3,
    "macd_signal": 120.2,
    "bb_upper": 48500,
    "bb_middle": 46500,
    "bb_lower": 44500,
    "sma_20": 46200,
    "ema_12": 46850
  },
  "sentiment_score": 0.65,
  "reasoning": "Bullish RSI, positive MACD crossover, sentiment positive at 0.65",
  "created_at": "2026-01-31T12:00:00Z"
}
```

#### Batch Predictions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict/batch` | POST | Generate predictions for all timeframes |

**Request:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "current_price": 46800.50,
  "prices": [45000, 45200, 45100, ...],  // Min 50 data points
  "sentiment_score": 0.65
}
```

**Response:**
```json
{
  "symbol": "BTC",
  "market_type": "crypto",
  "current_price": 46800.50,
  "predictions": [
    {
      "prediction_id": "uuid-1",
      "prediction_type": "30m",
      "predicted_price": 46900.00,
      "predicted_direction": "UP",
      "confidence_score": 70,
      "confidence_level": "MEDIUM",
      ...
    },
    {
      "prediction_id": "uuid-2",
      "prediction_type": "1h",
      "predicted_price": 47250.00,
      "predicted_direction": "UP",
      "confidence_score": 75,
      "confidence_level": "MEDIUM",
      ...
    },
    // 3h and 6h predictions...
  ]
}
```

### Pub/Sub Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pubsub-push/market-context` | POST | Pub/Sub push subscription endpoint |

Processes messages from Pub/Sub `market-context` topic and generates predictions.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_ML_PREDICTIONS` | `true` | Enable ML model predictions |
| `ENABLE_TECHNICAL_ANALYSIS` | `true` | Enable technical analysis |
| `ENABLE_CRYPTO_PREDICTIONS` | `true` | Enable crypto market predictions |
| `ENABLE_GOLD_PREDICTIONS` | `true` | Enable gold market predictions |
| `CORS_ORIGINS` | `https://sentilyze.live,...` | Allowed CORS origins |

## Prediction Timeframes

| Type | Description | Use Case |
|------|-------------|----------|
| `30m` | 30-minute prediction | Short-term scalping |
| `1h` | 1-hour prediction | Intraday trading |
| `3h` | 3-hour prediction | Swing trading |
| `6h` | 6-hour prediction | Position trading |

## Confidence Levels

| Score | Level | Description |
|-------|-------|-------------|
| 0-40 | LOW | Low confidence, high uncertainty |
| 41-70 | MEDIUM | Moderate confidence |
| 71-100 | HIGH | High confidence |

## Technical Indicators

- **RSI (14)**: Relative Strength Index
- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Upper, middle, lower bands
- **SMA (20)**: Simple Moving Average
- **EMA (12)**: Exponential Moving Average

## Running Locally

```bash
# Install dependencies
cd services/prediction-engine
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload --port 8084

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8084
```

## Docker

```bash
# Build from repo root
docker build -f services/prediction-engine/Dockerfile -t prediction-engine:3.0.0 .

# Run
docker run -p 8084:8084 prediction-engine:3.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8084/health

# Single prediction
curl -X POST http://localhost:8084/predict \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "market_type": "crypto",
    "current_price": 46800.50,
    "prices": [45000, 45200, 45100, 45300, ...],  // 50+ prices
    "sentiment_score": 0.65,
    "prediction_type": "1h"
  }'

# Batch predictions
curl -X POST http://localhost:8084/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "market_type": "crypto",
    "current_price": 46800.50,
    "prices": [45000, 45200, ...],  // 50+ prices
    "sentiment_score": 0.65
  }'
```

## Prediction Algorithm

```
┌──────────────────────────────────────────────────────────────┐
│                  Prediction Generation                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Input Validation                                          │
│     └─→ Check minimum 50 price data points                    │
│                                                               │
│  2. Technical Analysis                                        │
│     ├─→ Calculate RSI(14)                                     │
│     ├─→ Calculate MACD + Signal                               │
│     ├─→ Calculate Bollinger Bands                             │
│     ├─→ Calculate SMA(20) and EMA(12)                         │
│     └─→ Determine trend direction                             │
│                                                               │
│  3. Sentiment Integration                                     │
│     └─→ Factor in sentiment score (-1 to 1)                   │
│                                                               │
│  4. Price Prediction                                          │
│     ├─→ ML model (if enabled)                                 │
│     ├─→ Technical heuristic (fallback)                        │
│     └─→ Apply timeframe multiplier                            │
│                                                               │
│  5. Confidence Calculation                                    │
│     ├─→ Based on indicator agreement                          │
│     ├─→ Sentiment confidence                                  │
│     └─→ Historical accuracy (if available)                    │
│                                                               │
│  6. Output Generation                                         │
│     └─→ PredictionResult with all fields                      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
services/prediction-engine/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and enums
│   ├── models.py            # Prediction models
│   ├── predictor.py         # PredictionEngine
│   └── publisher.py         # Pub/Sub publishing
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Integration

### Upstream (Input)
- **Market Context Processor**: Publishes to `market-context` topic
- **Direct API**: Manual prediction requests

### Downstream (Output)
- **BigQuery**: Stores predictions for tracking
- **Pub/Sub**: Publishes to `predictions` topic
- **Tracker Service**: Monitors prediction outcomes

## License

MIT License - Sentilyze Team
