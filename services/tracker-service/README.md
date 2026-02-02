# Tracker Service

Prediction tracking and outcome evaluation service for validating prediction accuracy.

## Overview

This service tracks predictions over time and evaluates their accuracy when the prediction window expires. It calculates various accuracy metrics and can generate AI-powered analysis of prediction patterns.

## Features

- **Outcome Processing**: Calculate prediction accuracy vs actual price
- **Accuracy Statistics**: Direction accuracy, price difference, success levels
- **AI Analysis**: Optional AI-generated insights on prediction patterns
- **Pub/Sub Integration**: Event-driven prediction tracking
- **BigQuery Integration**: Stores predictions and outcomes for historical analysis
- **Success Level Classification**: None, Partial, Full success levels

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Tracker Service                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Outcome Endpoints                                           │
│  ├─→ /outcomes/process   - Process prediction outcome        │
│  └─→ /stats/accuracy     - Get accuracy statistics           │
│                                                              │
│  Pub/Sub Integration                                         │
│  └─→ /pubsub-push/predictions                               │
│       └─→ Store predictions for tracking                     │
│       └─→ Schedule outcome validation                        │
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
  "service": "tracker-service",
  "version": "3.0.0"
}
```

**Status Response:**
```json
{
  "service": "tracker-service",
  "ai_analysis_enabled": true,
  "tracking_enabled": true,
  "tracker_ready": true
}
```

### Outcomes

#### Process Outcome

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/outcomes/process` | POST | Process a prediction outcome |

**Request:**
```json
{
  "prediction_id": "uuid",
  "symbol": "BTC",
  "market_type": "crypto",
  "predicted_price": 47250.00,
  "predicted_direction": "UP",
  "current_price": 46800.50,
  "actual_price": 47100.00,
  "confidence_score": 75
}
```

**Response:**
```json
{
  "outcome_id": "uuid",
  "prediction_id": "uuid",
  "actual_direction": "UP",
  "price_diff": 300.50,
  "percent_diff": 0.64,
  "direction_correct": true,
  "success_level": "FULL",
  "ai_analysis_generated": false
}
```

### Statistics

#### Accuracy Stats

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats/accuracy` | GET | Get prediction accuracy statistics |

**Query Parameters:**
- `days` (int, default: 7): Number of days to analyze (1-365)
- `symbol` (string, optional): Filter by symbol
- `market_type` (string, optional): Filter by market type

**Response:**
```json
{
  "days": 7,
  "symbol": "BTC",
  "market_type": "crypto",
  "total_predictions": 150,
  "correct_directions": 112,
  "accuracy_percentage": 74.7,
  "by_period": [
    {
      "date": "2026-01-31",
      "total": 25,
      "correct": 20,
      "accuracy": 80.0
    }
  ],
  "generated_at": "2026-01-31T12:00:00Z"
}
```

### Pub/Sub Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pubsub-push/predictions` | POST | Pub/Sub push subscription endpoint |

Processes messages from Pub/Sub `predictions` topic and stores them for tracking.

## Success Levels

| Level | Description | Criteria |
|-------|-------------|----------|
| `NONE` | Prediction failed | Direction incorrect AND >2% price difference |
| `PARTIAL` | Partial success | Direction correct OR <2% price difference |
| `FULL` | Full success | Direction correct AND <1% price difference |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_AI_ANALYSIS` | `true` | Enable AI-powered outcome analysis |
| `ENABLE_AUTO_TRACKING` | `true` | Enable automatic prediction tracking |
| `CORS_ORIGINS` | `https://sentilyze.live,...` | Allowed CORS origins |

## Running Locally

```bash
# Install dependencies
cd services/tracker-service
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload --port 8087

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8087
```

## Docker

```bash
# Build from repo root
docker build -f services/tracker-service/Dockerfile -t tracker-service:3.0.0 .

# Run
docker run -p 8087:8087 tracker-service:3.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8087/health

# Process outcome
curl -X POST http://localhost:8087/outcomes/process \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_id": "test-pred-1",
    "symbol": "BTC",
    "market_type": "crypto",
    "predicted_price": 47250.00,
    "predicted_direction": "UP",
    "current_price": 46800.50,
    "actual_price": 47100.00,
    "confidence_score": 75
  }'

# Get accuracy stats
curl "http://localhost:8087/stats/accuracy?days=7&symbol=BTC"
```

## Outcome Calculation

```
┌──────────────────────────────────────────────────────────────┐
│                   Outcome Calculation                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Input:                                                       │
│  ├─→ Predicted price: $47,250                                 │
│  ├─→ Predicted direction: UP                                  │
│  ├─→ Current price (at prediction): $46,800.50                │
│  └─→ Actual price (after window): $47,100                     │
│                                                               │
│  Calculations:                                                │
│  ├─→ Actual direction: UP (actual > current)                  │
│  ├─→ Direction correct: true (predicted == actual)            │
│  ├─→ Price diff: $47,100 - $47,250 = -$150                    │
│  ├─→ Percent diff: -0.32%                                     │
│  └─→ Success level: FULL                                      │
│      (direction correct AND abs(percent_diff) < 1%)           │
│                                                               │
│  AI Analysis (if enabled):                                    │
│  └─→ Generate insights if confidence was low but correct      │
│      OR confidence was high but wrong                         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
services/tracker-service/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models.py            # PredictionRecord and Outcome models
│   └── tracker.py           # PredictionTracker
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Integration

### Upstream (Input)
- **Prediction Engine**: Publishes predictions to `predictions` topic
- **Direct API**: Manual outcome submissions

### Downstream (Output)
- **BigQuery**: Stores predictions and outcomes
- **AI Analysis**: Optional analysis generation

## Tracking Workflow

1. **Prediction Received**: Store prediction with timestamp and window
2. **Window Expires**: After prediction timeframe (1h, 6h, etc.)
3. **Outcome Calculation**: Compare predicted vs actual
4. **Metrics Update**: Update accuracy statistics
5. **AI Analysis**: Generate insights if enabled

## License

MIT License - Sentilyze Team
