# Sentiment Processor

AI-powered sentiment analysis service for crypto and gold markets using Vertex AI Gemini.

## Overview

This service processes market content (social media, news, articles) and performs sentiment analysis with market-specific prompts. It supports both crypto and gold markets with specialized analysis frameworks.

## Features

- **Multi-Market Support**: Crypto, Gold, and Generic market analysis
- **Vertex AI Gemini**: Advanced NLP sentiment analysis
- **Pub/Sub Integration**: Event-driven processing via push subscriptions
- **Cloud Run Compatible**: Scale-to-zero architecture
- **Deduplication**: Duplicate event detection and handling
- **Alert Generation**: Threshold-based sentiment alerts
- **COT Framework**: Commitment of Traders support for gold analysis
- **BigQuery Integration**: Raw and processed event storage

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Sentiment Processor                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Pub/Sub Push Endpoint                                       │
│  └─→ /pubsub-push/raw-events                                │
│       └─→ Message Parsing                                    │
│       └─→ Deduplication Check                                │
│       └─→ Market Type Detection (Crypto/Gold/Generic)        │
│       └─→ Sentiment Analysis (Vertex AI Gemini)              │
│       └─→ BigQuery Storage (Raw + Processed)                 │
│       └─→ Alert Publishing (if thresholds met)               │
│                                                              │
│  Manual Analysis Endpoint                                    │
│  └─→ /analyze                                               │
│       └─→ Direct text analysis                              │
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
  "service": "sentiment-processor",
  "version": "3.0.0"
}
```

**Ready Check Response:**
```json
{
  "status": "ready",
  "checks": {
    "analyzer": true,
    "pubsub": true,
    "bigquery": true,
    "publisher": true
  }
}
```

### Pub/Sub Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pubsub-push/raw-events` | POST | Pub/Sub push subscription endpoint |

Processes messages from Pub/Sub `raw-events` topic. Expects base64-encoded JSON payload.

### Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Analyze sentiment of provided text |

**Request:**
```json
{
  "text": "Bitcoin is showing strong bullish momentum!",
  "market_type": "crypto"
}
```

**Response:**
```json
{
  "predictionId": "uuid",
  "marketType": "crypto",
  "sentiment": {
    "score": 0.75,
    "label": "positive",
    "confidence": 0.92,
    "magnitude": 0.8
  },
  "entities": ["Bitcoin", "BTC"],
  "symbols": ["BTC"],
  "keywords": ["bullish", "momentum"]
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `GEMINI_MODEL` | `gemini-1.5-flash-001` | Vertex AI model name |
| `ENABLE_CRYPTO_ANALYSIS` | `true` | Enable crypto market analysis |
| `ENABLE_GOLD_ANALYSIS` | `true` | Enable gold market analysis |
| `ENABLE_COT_FRAMEWORK` | `false` | Enable COT framework for gold |
| `ENABLE_ALERTS` | `true` | Enable alert generation |
| `ALERT_MIN_CONFIDENCE` | `0.7` | Minimum confidence for alerts |
| `ALERT_POSITIVE_SCORE_THRESHOLD` | `0.5` | Positive sentiment threshold |
| `ALERT_NEGATIVE_SCORE_THRESHOLD` | `-0.5` | Negative sentiment threshold |
| `ALERT_COOLDOWN_SECONDS` | `3600` | Alert cooldown period |
| `ALERT_DEFAULT_CHANNELS` | `telegram` | Default alert channels |
| `ALERT_TELEGRAM_CHAT_IDS` | - | Comma-separated Telegram chat IDs |
| `CORS_ORIGINS` | `https://sentilyze.live,...` | Allowed CORS origins |

## Running Locally

```bash
# Install dependencies
cd services/sentiment-processor
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload --port 8082

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8082
```

## Docker

```bash
# Build from repo root
docker build -f services/sentiment-processor/Dockerfile -t sentiment-processor:3.0.0 .

# Run
docker run -p 8082:8082 sentiment-processor:3.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8082/health

# Analyze text
curl -X POST http://localhost:8082/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Bitcoin price is surging!", "market_type": "crypto"}'

# Pub/Sub push test
curl -X POST http://localhost:8082/pubsub-push/raw-events \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "data": "eyJldmVudF9pZCI6ICJ0ZXN0LTEiLCAiY29udGVudCI6ICJUZXN0IG1lc3NhZ2UiLCAic291cmNlIjogInR3aXR0ZXIifQ==",
      "messageId": "test-msg-1"
    }
  }'
```

## Message Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Raw Events  │────▶│  Pub/Sub     │────▶│ Sentiment        │
│  (Ingestion) │     │  Topic       │     │ Processor        │
└──────────────┘     └──────────────┘     └──────────────────┘
                                                   │
          ┌──────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│                    Processing Pipeline                   │
├──────────────────────────────────────────────────────────┤
│ 1. Parse Pub/Sub message                                 │
│ 2. Check deduplication (Redis cache)                     │
│ 3. Detect market type (crypto/gold/generic)              │
│ 4. Store raw event in BigQuery                           │
│ 5. Analyze sentiment with Vertex AI Gemini               │
│ 6. Transform to Silver layer format                      │
│ 7. Store processed event in BigQuery                     │
│ 8. Publish to processed-events topic                     │
│ 9. Generate alert if thresholds met                      │
└──────────────────────────────────────────────────────────┘
```

## Project Structure

```
services/sentiment-processor/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and market types
│   ├── analyzer.py          # UnifiedSentimentAnalyzer
│   ├── transformers.py      # Data transformation (Silver layer)
│   ├── publisher.py         # Pub/Sub publishing
│   └── prompts/             # Gemini prompts
│       ├── crypto.txt
│       └── gold.txt
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Key Components

### UnifiedSentimentAnalyzer
- Market-specific prompt selection
- Vertex AI Gemini integration
- Caching layer for performance
- Entity and keyword extraction

### DataTransformer
- Raw event to processed event transformation
- Silver layer BigQuery schema conversion
- Market type enrichment

### ResultsPublisher
- Pub/Sub message publishing
- Alert event routing
- Delivery tracking

## Integration

### Upstream (Input)
- **Ingestion Service**: Publishes raw events to `raw-events` topic

### Downstream (Output)
- **BigQuery**: Stores both raw and processed events
- **Pub/Sub**: Publishes to `processed-events` topic
- **Alert Service**: Receives alert events for threshold-based notifications

## Performance

- **Processing Time**: ~500ms per event (including API call)
- **Deduplication**: Redis-based with 7-day TTL
- **Concurrency**: Async processing with rate limiting
- **Memory**: ~512MB baseline

## License

MIT License - Sentilyze Team
