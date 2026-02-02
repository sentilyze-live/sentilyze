# Sentilyze - Unified Market Sentiment Analysis Platform

<p align="center">
  <strong>AI-Powered Sentiment Analysis & Prediction for Cryptocurrency and Gold Markets</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python: 3.9+">
  <img src="https://img.shields.io/badge/node-18+-green.svg" alt="Node.js: 18+">
  <img src="https://img.shields.io/badge/platform-GCP-orange.svg" alt="Platform: GCP">
</p>

---

## Overview

**Sentilyze** is a unified, cloud-native platform that combines advanced natural language processing (NLP) with financial market analysis to provide real-time sentiment analysis and price predictions for both **cryptocurrency** and **gold markets**. 

The platform ingests data from multiple sources (social media, news, market data), processes it through a sophisticated ML pipeline, and generates actionable predictions with confidence scoring.

### Key Features

- **Multi-Market Support**: Analyze both cryptocurrency (BTC, ETH, etc.) and gold markets from a unified platform
- **Real-time Processing**: Event-driven architecture using Google Pub/Sub for near real-time data processing
- **Advanced Sentiment Analysis**: Multi-model approach using Hugging Face transformers and OpenAI
- **ML-Powered Predictions**: Time-series forecasting with ensemble models
- **Comprehensive Analytics**: Historical analysis, accuracy tracking, and performance metrics
- **Flexible Alerting**: Email, Slack, and Discord notifications
- **Cloud-Native**: Built on Google Cloud Platform with auto-scaling and high availability

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                 │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│   Crypto     │    Gold      │    Social    │       News             │
│   Data       │    Data      │    Media     │                        │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────────────┘
       │              │              │                │
       └──────────────┴──────────────┴────────────────┘
                           │
                   ┌───────▼───────┐
                   │   Ingestion   │  ← Raw data collection & normalization
                   │   Service     │
                   └───────┬───────┘
                           │ Pub/Sub: raw-market-data
                   ┌───────▼───────┐
                   │   Sentiment   │  ← NLP processing, emotion detection
                   │   Processor   │
                   └───────┬───────┘
                           │ Pub/Sub: processed-sentiment
                   ┌───────▼───────┐
                   │Market Context │  ← Technical analysis, indicators
                   │   Processor   │
                   └───────┬───────┘
                           │ Pub/Sub: market-context
                   ┌───────▼───────┐
                   │   Prediction  │  ← ML models, ensemble forecasting
                   │    Engine     │
                   └───────┬───────┘
                           │ Pub/Sub: predictions
              ┌────────────┼────────────┐
       ┌───────▼───────┐   │   ┌───────▼───────┐
       │Alert Service  │   │   │  Tracker      │  ← Validation & accuracy tracking
       │               │   │   │   Service     │
       └───────┬───────┘   │   └───────┬───────┘
               │           │           │
       ┌───────▼───────┐   │   ┌───────▼───────┐
       │  External     │   │   │  BigQuery/    │
       │  Notifications│   │   │  PostgreSQL   │
       └───────────────┘   │   └───────────────┘
                           │
                   ┌───────▼───────┐
                   │API Gateway    │  ← Unified REST API
                   │               │
                   └───────┬───────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐   ┌───────▼────────┐  ┌──────▼──────┐
│ Analytics   │   │   Dashboard    │  │  External   │
│   Engine    │   │   (Future)     │  │    APIs     │
└─────────────┘   └────────────────┘  └─────────────┘
```

### Technology Stack

- **Cloud Platform**: Google Cloud Platform (GCP)
- **Compute**: Cloud Run (serverless containers)
- **Event Streaming**: Cloud Pub/Sub
- **Data Warehouse**: BigQuery
- **Cache**: Memorystore Redis
- **Database**: Cloud SQL (PostgreSQL)
- **ML/AI**: Vertex AI, Hugging Face, OpenAI
- **Container Registry**: Artifact Registry
- **CI/CD**: Cloud Build
- **Infrastructure as Code**: Terraform

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Cloud SDK (`gcloud`)
- Terraform >= 1.5.0
- Node.js >= 18 (for local development)
- Python >= 3.9 (for local development)

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/sentilyze.git
cd sentilyze

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Local Development with Docker Compose

```bash
# Start all services with emulators
make dev

# Or manually:
docker-compose up -d

# View logs
make dev-logs

# Stop services
make dev-stop
```

Access the services:
- **API Gateway**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs (when implemented)

### 3. GCP Deployment

```bash
# Initialize GCP project
gcloud config set project YOUR_PROJECT_ID

# Deploy infrastructure
make tf-init
make tf-apply

# Deploy services
make deploy
```

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| **API Gateway** | 8080 | REST API, request routing, authentication |
| **Ingestion** | 8081 | Data collection from multiple sources |
| **Sentiment Processor** | 8082 | NLP sentiment analysis |
| **Market Context** | 8083 | Technical analysis & indicators |
| **Prediction Engine** | 8084 | ML models & forecasting |
| **Alert Service** | 8085 | Notification management |
| **Tracker Service** | 8087 | Prediction validation |
| **Analytics Engine** | 8086 | Reporting & analytics |

## Environment Setup

### Feature Flags

Control which markets and features are enabled:

```env
# Market Enablement
ENABLE_CRYPTO_MARKET=true
ENABLE_GOLD_MARKET=true

# Prediction Types
ENABLE_CRYPTO_PREDICTIONS=true
ENABLE_GOLD_PREDICTIONS=true

# Alert Channels
ENABLE_EMAIL_ALERTS=true
ENABLE_SLACK_ALERTS=true
ENABLE_DISCORD_ALERTS=false
```

### API Keys Required

1. **Crypto Data**: CoinMarketCap, CoinAPI, or CryptoCompare
2. **Gold Data**: Gold API or Metals API
3. **Social Media**: Twitter API v2, Reddit API
4. **News**: NewsAPI, Bloomberg (optional)
5. **ML/AI**: Hugging Face, OpenAI (optional)

## Development

### Building Services

```bash
# Build all services
make build

# Build specific service
make build-api-gateway
```

### Testing

```bash
# Run all tests
make test

# Test specific service
make test-api-gateway
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Type checking
make typecheck
```

### Infrastructure Management

```bash
# Initialize Terraform
make tf-init

# Plan changes
make tf-plan

# Apply changes
make tf-apply

# Destroy infrastructure
make tf-destroy
```

## Documentation

- **[Architecture](ARCHITECTURE.md)** - Detailed architecture and data flow
- **[Deployment](DEPLOYMENT.md)** - Production deployment guide
- **API Documentation** - Available at `/docs` endpoint (when implemented)

## Monitoring

- **Cloud Monitoring**: Metrics, alerts, and dashboards in GCP
- **BigQuery**: Historical data analysis and reporting
- **Cloud Logging**: Centralized logging across all services

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Crypto Market Data**: CoinMarketCap API
- **Gold Market Data**: Gold API
- **Sentiment Analysis**: Hugging Face Transformers
- **Cloud Infrastructure**: Google Cloud Platform

## Support

For support, email support@sentilyze.com or join our Slack channel.

---

<p align="center">
  Built with ❤️ for the trading community
</p>
