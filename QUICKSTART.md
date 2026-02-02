# Sentilyze Quick Start Guide

Welcome to Sentilyze! This guide will help you get up and running quickly with the unified sentiment analysis platform.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Python** (v3.9+)
- **Git**
- **gcloud CLI** (for GCP deployments)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/sentilyze.git
cd sentilyze
```

### 2. Start Local Services

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start all services
./scripts/deploy-local.sh up
```

This will:
- Start PostgreSQL database
- Start Redis cache
- Build and start the API service
- Run database migrations
- Perform health checks

### 3. Access the Services

Once running, you can access:

- **API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **PGAdmin**: http://localhost:5050 (admin@admin.com / admin)
- **Redis**: localhost:6379

### 4. Test the API

```bash
# Health check
curl http://localhost:8080/health

# Analyze sentiment
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "This is amazing!", "language": "en"}'
```

## Configuration

### Environment Variables

Create a `.env.local` file for local development:

```bash
# Database
DATABASE_URL=postgresql://sentilyze:sentilyze@localhost:5432/sentilyze
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_PORT=8080
API_HOST=0.0.0.0
DEBUG=true
LOG_LEVEL=debug

# Secrets (add your own)
OPENAI_API_KEY=your-key-here
JWT_SECRET=your-jwt-secret
```

## GCP Deployment

### 1. Initial GCP Setup

```bash
# Set up GCP project (run once)
./scripts/setup-gcp.sh <your-project-id>
```

### 2. Configure Secrets

```bash
# List all secrets
./scripts/manage-secrets.sh list

# Create/update secrets
./scripts/manage-secrets.sh create openai-api-key
./scripts/manage-secrets.sh update jwt-secret "your-secret-value"
```

### 3. Deploy to Cloud Run

```bash
# Deploy to development
./scripts/deploy.sh dev

# Deploy to production
./scripts/deploy.sh prod $(git describe --tags)
```

### 4. Verify Deployment

```bash
# Run health checks
./scripts/health-check.sh --environment dev
```

## Project Structure

```
sentilyze/
├── docker/                 # Docker configurations
├── scripts/               # Deployment and utility scripts
│   ├── deploy.sh          # Main GCP deployment
│   ├── deploy-local.sh    # Local deployment
│   ├── setup-gcp.sh       # GCP initial setup
│   ├── health-check.sh    # Service health checks
│   ├── manage-secrets.sh  # Secret management
│   ├── data-retention.sh  # Data cleanup
│   └── load-test.sh       # Load testing
├── tools/                 # Python utilities
│   ├── bq_setup.py        # BigQuery setup
│   ├── pubsub_setup.py    # Pub/Sub setup
│   └── migrate-db.py      # Database migrations
├── migrations/            # Database migrations
├── services/              # Application services
│   ├── api/              # REST API service
│   ├── worker/           # Background worker
│   └── scheduler/        # Job scheduler
├── tests/                # Test suites
└── docs/                 # Documentation
```

## Common Commands

### Local Development

```bash
# Start services
./scripts/deploy-local.sh up

# View logs
./scripts/deploy-local.sh logs

# Restart services
./scripts/deploy-local.sh restart

# Run migrations
./scripts/deploy-local.sh migrate

# Open shell in container
./scripts/deploy-local.sh shell api

# Clean up (removes all data!)
./scripts/deploy-local.sh clean
```

### Database Operations

```bash
# Check migration status
python tools/migrate-db.py --environment local status

# Run pending migrations
python tools/migrate-db.py --environment local migrate

# Rollback last migration
python tools/migrate-db.py --environment local rollback 1

# Create new migration
python tools/migrate-db.py --environment local create add_users_table
```

### Monitoring & Testing

```bash
# Run health checks
./scripts/health-check.sh --environment local

# Run load tests
./scripts/load-test.sh health
./scripts/load-test.sh analyze --users 50 --duration 60

# Run data retention
./scripts/data-retention.sh --dry-run
```

## Troubleshooting

### Services Won't Start

1. Check Docker is running:
   ```bash
   docker ps
   ```

2. Check logs:
   ```bash
   ./scripts/deploy-local.sh logs
   ```

3. Clean and restart:
   ```bash
   ./scripts/deploy-local.sh clean
   ./scripts/deploy-local.sh up
   ```

### Database Connection Issues

1. Check PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Verify connection string in `.env.local`

3. Reset database:
   ```bash
   docker-compose down -v
   ./scripts/deploy-local.sh up
   ```

### Migration Failures

1. Check status:
   ```bash
   python tools/migrate-db.py --environment local status
   ```

2. Fix the issue and re-run:
   ```bash
   python tools/migrate-db.py --environment local migrate
   ```

3. If stuck, rollback:
   ```bash
   python tools/migrate-db.py --environment local rollback 1
   ```

## Next Steps

- Read the [API Documentation](http://localhost:8080/docs)
- Check out [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Review [CHANGELOG.md](CHANGELOG.md) for version history

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-org/sentilyze/issues)
- **Documentation**: See `/docs` directory
- **Support**: support@sentilyze.com

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.
