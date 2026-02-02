# Unified API Gateway

Version 4.0.0 - Merged from Gold and v3 projects

## Overview

This unified API Gateway combines the best features from both the Sentilyze-Gold and Sentilyze-v3 projects:

- **From Gold**: Advanced authentication (JWT + API Keys), comprehensive rate limiting, audit logging, enhanced security features
- **From v3**: Clean structure, admin endpoints with metrics, optional authentication support, WebSocket origin checking

## Features

### Authentication
- JWT token-based authentication
- API Key authentication (X-API-Key header)
- Optional authentication for public endpoints
- Role-based access control (admin, user)

### Security
- Rate limiting with Redis/memory fallback
- Input sanitization and validation
- Audit logging for sensitive operations
- CORS configuration
- Security headers

### Routes (Feature Flags)
- `/crypto/*` - Crypto market endpoints (enable with `FEATURE_CRYPTO_ROUTES`)
- `/gold/*` - Gold market endpoints (enable with `FEATURE_GOLD_ROUTES`)
- `/sentiment/*` - Unified sentiment analysis (enable with `FEATURE_SENTIMENT_ROUTES`)
- `/analytics/*` - Analytics and correlation (enable with `FEATURE_ANALYTICS_ROUTES`)
- `/admin/*` - Admin endpoints (enable with `FEATURE_ADMIN_ROUTES`)
- `/auth/*` - Authentication endpoints (always enabled)
- `/health`, `/ready`, `/live` - Health checks (always enabled)
- `/ws` - WebSocket endpoint (enable with `FEATURE_WEBSOCKET`)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Sentilyze API Gateway | Application name |
| `APP_VERSION` | 4.0.0 | Application version |
| `ENVIRONMENT` | development | Environment (development/staging/production) |
| `LOG_LEVEL` | INFO | Logging level |
| `JWT_SECRET` | None | JWT secret key |
| `ADMIN_API_KEY` | None | Admin API key |
| `ADMIN_SECRET_KEY` | None | Admin dashboard secret |
| `RATE_LIMIT_REQUESTS` | 100 | Max requests per window |
| `RATE_LIMIT_WINDOW` | 60 | Rate limit window (seconds) |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `ALLOWED_ORIGINS` | * | Comma-separated CORS origins |
| `GOOGLE_CLOUD_PROJECT` | None | GCP project ID |
| `BIGQUERY_DATASET` | None | BigQuery dataset |
| `FEATURE_CRYPTO_ROUTES` | true | Enable crypto routes |
| `FEATURE_GOLD_ROUTES` | true | Enable gold routes |
| `FEATURE_SENTIMENT_ROUTES` | true | Enable sentiment routes |
| `FEATURE_ANALYTICS_ROUTES` | true | Enable analytics routes |
| `FEATURE_ADMIN_ROUTES` | true | Enable admin routes |
| `FEATURE_WEBSOCKET` | true | Enable WebSocket |

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /ready` - Readiness check with dependency validation
- `GET /live` - Liveness check

### Authentication
- `POST /auth/token` - Get JWT token
- `GET /auth/me` - Get current user info
- `GET /auth/verify` - Verify token validity
- `POST /auth/refresh` - Refresh token

### Crypto
- `GET /crypto/price/{symbol}` - Get crypto price
- `GET /crypto/prices` - Get multiple crypto prices
- `GET /crypto/sentiment/{symbol}` - Get crypto sentiment
- `GET /crypto/trending` - Get trending cryptocurrencies
- `GET /crypto/market-overview` - Get market overview

### Gold
- `GET /gold/price/{symbol}` - Get gold price
- `GET /gold/prices` - Get all gold prices
- `GET /gold/sentiment/{symbol}` - Get gold sentiment
- `GET /gold/context/{symbol}` - Get market context
- `GET /gold/correlation/{symbol}` - Get correlation analysis
- `GET /gold/predictions/{symbol}` - Get AI predictions

### Sentiment
- `GET /sentiment/symbol/{symbol}` - Get sentiment data
- `GET /sentiment/symbol/{symbol}/aggregate` - Get aggregated sentiment
- `GET /sentiment/symbol/{symbol}/latest` - Get latest sentiment
- `GET /sentiment/trending` - Get trending symbols
- `GET /sentiment/market-sentiment` - Get overall market sentiment

### Analytics
- `GET /analytics/correlation/{symbol}` - Sentiment-price correlation
- `GET /analytics/sentiment-distribution/{symbol}` - Sentiment distribution
- `GET /analytics/volume/{symbol}` - Mention volume
- `GET /analytics/compare` - Compare multiple symbols
- `POST /analytics/granger-test` - Granger causality test

### Admin
- `GET /admin/health` - Admin health check
- `GET /admin/config` - Get configuration
- `POST /admin/features/{feature}/toggle` - Toggle feature flags
- `GET /admin/stats` - Get system statistics
- `POST /admin/cache/clear` - Clear cache
- `GET /admin/logs` - Get recent logs

## Running Locally

```bash
# Install dependencies
cd services/api-gateway
poetry install

# Run with uvicorn
poetry run uvicorn src.main:app --reload

# Or with Python directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Docker

```bash
# Build from repo root
docker build -f services/api-gateway/Dockerfile -t api-gateway:4.0.0 .

# Run
docker run -p 8000:8000 api-gateway:4.0.0
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Get crypto price
curl http://localhost:8000/crypto/price/BTC

# Get gold price
curl http://localhost:8000/gold/price/XAUUSD

# Get sentiment
curl http://localhost:8000/sentiment/symbol/BTC
```

## Architecture

```
api-gateway/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with lifespan
│   ├── config.py            # Settings with feature flags
│   ├── auth.py              # JWT + API Key auth
│   ├── logging.py           # Structured logging
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py          # Auth middleware
│   │   └── rate_limit.py    # Rate limiting
│   └── routes/
│       ├── __init__.py      # Router registration
│       ├── auth.py          # Auth endpoints
│       ├── health.py        # Health checks
│       ├── crypto.py        # Crypto routes
│       ├── gold.py          # Gold routes
│       ├── sentiment.py     # Unified sentiment
│       ├── analytics.py     # Analytics
│       └── admin.py         # Admin endpoints
├── pyproject.toml
├── Dockerfile
└── README.md
```

## License

Proprietary - Sentilyze Team
