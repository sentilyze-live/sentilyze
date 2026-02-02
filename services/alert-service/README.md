# Alert Service

Notification and alerting service for crypto and gold markets with multi-channel support.

## Overview

This service receives alert events and routes them to configured notification channels (Telegram, Webhook). It supports idempotent delivery with deduplication and cooldown mechanisms.

## Features

- **Multi-Channel Support**: Telegram and Webhook notifications
- **Pub/Sub Integration**: Event-driven alert processing
- **Idempotent Delivery**: Duplicate alert detection and prevention
- **Cooldown Mechanism**: Rate limiting per alert type/symbol
- **BigQuery Integration**: Alert history storage
- **Test Endpoints**: Send test alerts to verify configuration
- **Severity Levels**: Critical, High, Medium, Low severity classification

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Alert Service                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Alert Endpoints                                             │
│  ├─→ /alerts             - Create and send alert             │
│  └─→ /test/telegram      - Send test Telegram alert          │
│                                                              │
│  Pub/Sub Integration                                         │
│  └─→ /pubsub-push/alerts                                    │
│       └─→ Process alerts from Pub/Sub                        │
│       └─→ Route to configured channels                       │
│       └─→ Deduplicate and apply cooldowns                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/ready` | GET | Readiness check with channel validation |
| `/status` | GET | Service status and channel configuration |

**Health Check Response:**
```json
{
  "status": "healthy",
  "service": "alert-service",
  "version": "3.0.0"
}
```

**Status Response:**
```json
{
  "service": "alert-service",
  "telegram_enabled": true,
  "webhook_enabled": true,
  "telegram_ready": true,
  "webhook_ready": true
}
```

### Alerts

#### Create Alert

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/alerts` | POST | Create and send an alert |

**Request:**
```json
{
  "alert_type": "sentiment_positive",
  "severity": "medium",
  "title": "BTC: Positive Sentiment Detected",
  "message": "score=0.75 label=positive confidence=0.92 source=twitter",
  "data": {
    "symbol": "BTC",
    "score": 0.75,
    "label": "positive",
    "confidence": 0.92
  },
  "channels": ["telegram"],
  "recipients": ["123456789"]
}
```

**Response:**
```json
{
  "status": "created",
  "alert_id": "uuid"
}
```

#### Pub/Sub Push

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pubsub-push/alerts` | POST | Pub/Sub push subscription endpoint |

Processes messages from Pub/Sub `alerts` topic with automatic channel routing.

### Testing

#### Test Telegram

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/test/telegram` | POST | Send a test alert to Telegram |

**Query Parameters:**
- `chat_id` (string, required): Telegram chat ID
- `message` (string, optional): Custom test message

**Response:**
```json
{
  "success": true,
  "chat_id": "123456789",
  "message": "Test alert from Sentilyze"
}
```

## Alert Event Format

```json
{
  "alert_id": "uuid",
  "alert_type": "sentiment_positive",
  "severity": "medium",
  "title": "BTC: Positive Sentiment Detected",
  "message": "Detailed message about the alert",
  "data": {
    "symbol": "BTC",
    "event_id": "uuid",
    "score": 0.75
  },
  "channels": ["telegram", "webhook"],
  "recipients": ["123456789"],
  "tenant_id": "default"
}
```

## Severity Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `critical` | Critical condition | System failure, major anomaly |
| `high` | High priority | Significant sentiment shift |
| `medium` | Medium priority | Notable event |
| `low` | Low priority | Informational |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_TELEGRAM` | `true` | Enable Telegram notifications |
| `ENABLE_WEBHOOK` | `true` | Enable webhook notifications |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token |
| `TELEGRAM_CHAT_IDS` | - | Comma-separated default chat IDs |
| `WEBHOOK_URL` | - | Default webhook URL |
| `ALERT_DEFAULT_CHANNELS` | `telegram` | Default channels for alerts |
| `CORS_ORIGINS` | `https://sentilyze.live,...` | Allowed CORS origins |

## Running Locally

```bash
# Install dependencies
cd services/alert-service
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload --port 8085

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8085
```

## Docker

```bash
# Build from repo root
docker build -f services/alert-service/Dockerfile -t alert-service:3.0.0 .

# Run
docker run -p 8085:8085 alert-service:3.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8085/health

# Create alert
curl -X POST http://localhost:8085/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "test",
    "severity": "low",
    "title": "Test Alert",
    "message": "This is a test alert",
    "channels": ["telegram"],
    "recipients": ["YOUR_CHAT_ID"]
  }'

# Test Telegram
curl -X POST "http://localhost:8085/test/telegram?chat_id=YOUR_CHAT_ID&message=Hello%20from%20Sentilyze"
```

## Alert Processing Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Alert Processing                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Alert Received                                            │
│     └─→ Parse AlertEvent from Pub/Sub or API                  │
│                                                               │
│  2. Persistence                                               │
│     └─→ Store alert in BigQuery                               │
│                                                               │
│  3. Channel Resolution                                        │
│     ├─→ Use alert.channels if provided                        │
│     └─→ Fallback to ALERT_DEFAULT_CHANNELS                    │
│                                                               │
│  4. Deduplication                                             │
│     └─→ Check Redis cache for sent:{alert_id}:{channel}       │
│     └─→ Skip if already sent (7-day TTL)                      │
│                                                               │
│  5. Delivery                                                  │
│     ├─→ Telegram: Send to each recipient                      │
│     └─→ Webhook: POST to webhook URL                          │
│                                                               │
│  6. Confirmation                                              │
│     └─→ Cache sent status                                     │
│     └─→ Log delivery result                                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
services/alert-service/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and enums
│   └── notifier.py          # NotifierManager (Telegram, Webhook)
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Integration

### Upstream (Input)
- **Sentiment Processor**: Publishes sentiment-based alerts
- **Market Context Processor**: Publishes anomaly alerts
- **Direct API**: Manual alert creation

### Downstream (Output)
- **Telegram**: Chat notifications
- **Webhook**: HTTP POST callbacks
- **BigQuery**: Alert history storage

## Telegram Message Format

```
🟡 <b>Sentiment Alert</b>

<b>BTC: Positive Sentiment Detected</b>

score=0.75 label=positive confidence=0.92 source=twitter

<code>2026-01-31 12:00:00 UTC</code>
```

## License

MIT License - Sentilyze Team
