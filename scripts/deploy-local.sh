#!/bin/bash
###############################################################################
# Script: deploy-local.sh
# Description: Local development deployment script
# Usage: ./deploy-local.sh [command]
# Commands:
#   up      - Start all services (default)
#   down    - Stop all services
#   restart - Restart all services
#   logs    - View logs
#   shell   - Open shell in container
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
ENV_FILE="${PROJECT_ROOT}/.env.local"
COMMAND="${1:-up}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

###############################################################################
# Setup Environment
###############################################################################
setup_environment() {
    log_info "Setting up local environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create .env.local if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning ".env.local not found. Creating from template..."
        cat > "$ENV_FILE" << EOF
# Sentilyze Local Environment Configuration
ENVIRONMENT=local
DEBUG=true
LOG_LEVEL=debug

# Database
DATABASE_URL=postgresql://sentilyze:sentilyze@postgres:5432/sentilyze
REDIS_URL=redis://redis:6379/0

# API Configuration
API_PORT=8080
API_HOST=0.0.0.0

# BigQuery (for local development, use emulator or skip)
BIGQUERY_PROJECT_ID=local-project
BIGQUERY_DATASET=sentilyze_local

# Pub/Sub (for local development, use emulator or skip)
PUBSUB_PROJECT_ID=local-project
PUBSUB_EMULATOR_HOST=pubsub:8085

# Secrets
SECRET_KEY=local-dev-secret-key-change-in-production
JWT_SECRET=local-dev-jwt-secret-change-in-production

# External APIs (add your development keys)
# OPENAI_API_KEY=your-key-here
# GOOGLE_CLOUD_API_KEY=your-key-here
EOF
        log_success "Created .env.local"
        log_warning "Please update .env.local with your actual API keys"
    fi
    
    # Check Docker Compose file
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yml not found in project root"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p "${PROJECT_ROOT}/data/postgres"
    mkdir -p "${PROJECT_ROOT}/data/redis"
    mkdir -p "${PROJECT_ROOT}/logs"
    
    log_success "Environment setup complete"
}

###############################################################################
# Start Services
###############################################################################
start_services() {
    log_info "Starting Docker Compose services..."
    
    cd "$PROJECT_ROOT"
    
    # Pull latest images
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull 2>/dev/null || true
    
    # Build local images
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --parallel
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    log_success "Services started"
    
    # Run health checks
    sleep 5
    health_checks
}

###############################################################################
# Stop Services
###############################################################################
stop_services() {
    log_info "Stopping Docker Compose services..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    
    log_success "Services stopped"
}

###############################################################################
# Restart Services
###############################################################################
restart_services() {
    log_info "Restarting services..."
    stop_services
    start_services
}

###############################################################################
# View Logs
###############################################################################
view_logs() {
    log_info "Viewing logs (Ctrl+C to exit)..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

###############################################################################
# Open Shell
###############################################################################
open_shell() {
    local service="${2:-api}"
    
    log_info "Opening shell in ${service} container..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" /bin/bash || \
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" /bin/sh
}

###############################################################################
# Run Migrations
###############################################################################
run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Wait for database to be ready
    log_info "Waiting for database..."
    for i in {1..30}; do
        if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
            pg_isready -U sentilyze > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Run migrations
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec api \
        python tools/migrate-db.py --environment local migrate
    
    log_success "Migrations completed"
}

###############################################################################
# Health Checks
###############################################################################
health_checks() {
    log_info "Running health checks..."
    
    local failed=0
    
    # Check PostgreSQL
    log_info "Checking PostgreSQL..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        pg_isready -U sentilyze > /dev/null 2>&1; then
        log_success "PostgreSQL is healthy"
    else
        log_error "PostgreSQL is not responding"
        failed=1
    fi
    
    # Check Redis
    log_info "Checking Redis..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T redis \
        redis-cli ping | grep -q "PONG"; then
        log_success "Redis is healthy"
    else
        log_error "Redis is not responding"
        failed=1
    fi
    
    # Check API
    log_info "Checking API..."
    if curl -s http://localhost:8080/health | grep -q "ok"; then
        log_success "API is healthy"
    else
        log_error "API is not responding"
        failed=1
    fi
    
    if [[ $failed -eq 0 ]]; then
        log_success "All health checks passed!"
        echo ""
        log_info "Services are running at:"
        log_info "  API:      http://localhost:8080"
        log_info "  API Docs: http://localhost:8080/docs"
        log_info "  PGAdmin:  http://localhost:5050"
        log_info "  Redis:    localhost:6379"
    else
        log_error "Some health checks failed. Check logs with: ./deploy-local.sh logs"
        return 1
    fi
}

###############################################################################
# Clean Up
###############################################################################
clean_up() {
    log_warning "This will remove all containers, volumes, and data!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [[ "$confirm" == "yes" ]]; then
        cd "$PROJECT_ROOT"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v
        rm -rf "${PROJECT_ROOT}/data"
        rm -rf "${PROJECT_ROOT}/logs"
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

###############################################################################
# Main Execution
###############################################################################
main() {
    log_info "========================================="
    log_info "Sentilyze Local Deployment"
    log_info "Command: ${COMMAND}"
    log_info "========================================="
    
    case "$COMMAND" in
        up|start)
            setup_environment
            start_services
            run_migrations
            ;;
        down|stop)
            stop_services
            ;;
        restart)
            restart_services
            run_migrations
            ;;
        logs)
            view_logs
            ;;
        shell)
            open_shell "$@"
            ;;
        migrate)
            run_migrations
            ;;
        health)
            health_checks
            ;;
        clean)
            clean_up
            ;;
        *)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  up, start   - Start all services"
            echo "  down, stop  - Stop all services"
            echo "  restart     - Restart all services"
            echo "  logs        - View logs"
            echo "  shell       - Open shell in container"
            echo "  migrate     - Run database migrations"
            echo "  health      - Run health checks"
            echo "  clean       - Clean up all data"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
