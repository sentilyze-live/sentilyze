# Sentilyze Admin Panel

Full-stack admin panel for monitoring and managing the Sentilyze platform.

## Features

- **System Monitoring**: Real-time service health, CPU/memory metrics, uptime tracking
- **Data Analytics Dashboard**: BigQuery data visualization, prediction accuracy, sentiment trends
- **Service Management**: Service control, configuration, log viewing, manual job triggering
- **User Management**: User CRUD, role-based access control, API key management, audit logs

## Technology Stack

### Backend
- FastAPI 0.109+
- PostgreSQL (SQLAlchemy + Alembic)
- JWT Authentication
- WebSocket (real-time updates)
- Prometheus metrics

### Frontend
- Next.js 14+ (App Router)
- Shadcn/ui + Tailwind CSS
- React Query + Zustand
- Recharts + ECharts
- TypeScript

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL

### Installation

1. Install Python dependencies:
```bash
cd services/admin-panel
poetry install
```

2. Setup database:
```bash
poetry run alembic upgrade head
```

3. Run development server:
```bash
poetry run uvicorn src.main:app --reload --port 8090
```

4. Access API docs:
```
http://localhost:8090/docs
```

## Default Credentials

```
Username: admin
Password: admin123
```

**WARNING**: Change these credentials in production!

## API Endpoints

- `POST /api/v1/auth/login` - User login
- `GET /api/v1/services` - List all services
- `GET /api/v1/analytics/sentiment` - Sentiment overview
- `GET /api/v1/metrics/system` - System metrics
- `GET /api/v1/users` - User management
- `WS /api/v1/ws` - Real-time WebSocket

See `/docs` for full API documentation.

## Development

### Run tests
```bash
poetry run pytest
```

### Code formatting
```bash
poetry run black src/
poetry run isort src/
```

### Type checking
```bash
poetry run mypy src/
```

## Docker

Build and run with Docker:
```bash
docker build -t sentilyze-admin-panel .
docker run -p 8090:8090 sentilyze-admin-panel
```

Or use docker-compose:
```bash
docker-compose up admin-panel
```

## License

MIT
