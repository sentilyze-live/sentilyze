# Unified Ingestion Service

A unified data ingestion service for Sentilyze that supports both cryptocurrency and precious metals data collection.

## Overview

This service merges collectors from both the v3 (crypto) and Gold projects into a single unified service:

- **v3 Collectors (Crypto)**: Reddit, RSS, Binance
- **Gold Collectors**: GoldAPI, Finnhub, Turkish Scrapers

## Features

- Unified collector base class with common interface
- Feature flags to enable/disable specific collectors
- Support for both crypto and gold data sources
- Circuit breaker protection for external APIs
- Scheduled and on-demand collection
- Pub/Sub integration for event streaming
- FastAPI-based REST API
- APScheduler for periodic collection

## Quick Start

### Installation

```bash
cd services/ingestion
poetry install
```

### Environment Variables

Create a `.env` file with the following variables:

```env
# General
ENVIRONMENT=development
LOG_LEVEL=INFO
INGESTION_ADMIN_API_KEY=your-admin-key

# Feature Flags
ENABLE_REDDIT_COLLECTOR=false
ENABLE_RSS_COLLECTOR=true
ENABLE_BINANCE_COLLECTOR=false
ENABLE_GOLDAPI_COLLECTOR=true
ENABLE_FINNHUB_COLLECTOR=true
ENABLE_TURKISH_SCRAPERS=true
ENABLE_SCHEDULER=true

# API Keys
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
BINANCE_API_KEY=your-binance-api-key
GOLDAPI_API_KEY=your-goldapi-key
FINNHUB_API_KEY=your-finnhub-key

# Scheduler Intervals (seconds)
SCHEDULER_REDDIT_INTERVAL=600
SCHEDULER_RSS_INTERVAL=300
SCHEDULER_BINANCE_INTERVAL=60
SCHEDULER_GOLDAPI_INTERVAL=60
SCHEDULER_FINNHUB_INTERVAL=300
SCHEDULER_TURKISH_INTERVAL=300
```

### Running the Service

```bash
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t unified-ingestion-service .
docker run -p 8000:8000 --env-file .env unified-ingestion-service
```

## API Endpoints

### Health & Status

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /status` - Collector status and metrics

### Manual Collection

- `POST /collect/reddit` - Trigger Reddit collection
- `POST /collect/rss` - Trigger RSS collection
- `POST /collect/binance` - Trigger Binance collection
- `POST /collect/goldapi` - Trigger GoldAPI collection
- `POST /collect/finnhub` - Trigger Finnhub collection
- `POST /collect/turkish` - Trigger Turkish scrapers collection
- `POST /collect/all` - Trigger all collectors

### Configuration

- `GET /collectors/{name}/config` - Get collector configuration

## Collectors

### Reddit Collector
Collects posts from crypto-related subreddits using PRAW.
- Tracks: BTC, ETH, BNB, SOL, ADA, XRP, DOT, DOGE, AVAX, MATIC, LINK, UNI, LTC, ATOM, ETC
- Subreddits: Bitcoin, ethereum, CryptoCurrency, CryptoMarkets, BitcoinMarkets, altcoin, defi, NFTs

### RSS Collector
Collects news from crypto RSS feeds.
- Feeds: CoinTelegraph, CoinDesk, CryptoNews, Decrypt, Bitcoin Magazine

### Binance Collector
Collects market data from Binance via REST API and WebSocket.
- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT, XRPUSDT
- Features: 24hr ticker data, real-time WebSocket streaming

### GoldAPI Collector
Collects precious metals spot prices from GoldAPI.io.
- Metals: XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium)
- Currencies: USD, EUR, GBP, TRY, JPY, CHF

### Finnhub Collector
Collects gold-related financial news from Finnhub.
- Symbols: GLD, IAU, GC=F, XAU, GC
- Features: Gold keyword filtering, rate limiting

### Turkish Scrapers
Collects gold and currency prices from Turkish sources.
- Sources: Truncgil (API), Harem Altın, Nadir Döviz, TCMB (Central Bank)
- Data: Gram gold, Ons gold, USD/TRY, EUR/TRY

## Architecture

```
services/ingestion/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Service configuration
│   ├── publisher.py         # Pub/Sub message publisher
│   ├── scheduler.py         # APScheduler configuration
│   └── collectors/
│       ├── __init__.py      # Collector registry
│       ├── base.py          # Base collector classes
│       ├── reddit.py        # Reddit collector
│       ├── rss.py           # RSS collector
│       ├── binance.py       # Binance collector
│       ├── goldapi.py       # GoldAPI collector
│       ├── finnhub.py       # Finnhub collector
│       ├── turkish_scrapers.py    # Turkish scrapers wrapper
│       └── turkish_sources/       # Individual Turkish scrapers
│           ├── __init__.py
│           ├── truncgil.py
│           ├── harem_altin.py
│           ├── nadir_doviz.py
│           └── tcmb.py
├── pyproject.toml
├── Dockerfile
└── README.md
```

## License

MIT
