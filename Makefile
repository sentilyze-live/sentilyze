# Sentilyze - Unified Market Sentiment Analysis Platform
# Makefile for build automation

.PHONY: help install dev build test lint clean deploy setup

# ============================================
# Default Target
# ============================================
help: ## Display this help message
	@echo "Sentilyze - Unified Market Sentiment Analysis Platform"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================
# Environment Setup
# ============================================
setup: ## Initial project setup - install dependencies and configure environment
	@echo "Setting up Sentilyze project..."
	@cp .env.example .env 2>/dev/null || echo ".env already exists"
	@echo "Please edit .env file with your configuration"
	$(MAKE) install

install: ## Install all dependencies
	@echo "Installing service dependencies..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			echo "Installing Node.js dependencies for $$dir..."; \
			cd "$$dir" && npm install && cd ../..; \
		elif [ -f "$$dir/requirements.txt" ]; then \
			echo "Installing Python dependencies for $$dir..."; \
			cd "$$dir" && pip install -r requirements.txt && cd ../..; \
		fi \
	done

# ============================================
# Local Development
# ============================================
dev: ## Start all services in development mode with Docker Compose
	@echo "Starting development environment..."
	@docker-compose up -d firestore-emulator postgres bigquery-emulator pubsub-emulator
	@echo "Waiting for services to be ready..."
	@sleep 10
	@docker-compose up -d
	@echo "Services started!"
	@echo "API Gateway: http://localhost:8080"

dev-build: ## Build and start all services
	@echo "Building and starting development environment..."
	@docker-compose up -d --build

dev-logs: ## View logs from all services
	@docker-compose logs -f

dev-stop: ## Stop all development services
	@echo "Stopping development environment..."
	@docker-compose down

dev-clean: ## Stop and remove all containers, volumes, and networks
	@echo "Cleaning up development environment..."
	@docker-compose down -v --remove-orphans

# ============================================
# Individual Services
# ============================================
services = api-gateway ingestion sentiment-processor market-context-processor prediction-engine alert-service tracker-service analytics-engine

$(services):
	@echo "Starting $@ service..."
	@docker-compose up -d $@

# ============================================
# Building
# ============================================
build: ## Build all service Docker images
	@echo "Building all service images..."
	@docker-compose build

build-%: ## Build specific service (e.g., build-api-gateway)
	@echo "Building $* image..."
	@docker-compose build $*

# ============================================
# Testing
# ============================================
test: ## Run all tests
	@echo "Running tests for all services..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			echo "Testing $$dir..."; \
			cd "$$dir" && npm test && cd ../..; \
		elif [ -f "$$dir/requirements.txt" ]; then \
			echo "Testing $$dir..."; \
			cd "$$dir" && pytest && cd ../..; \
		fi \
	done

test-%: ## Run tests for specific service (e.g., test-api-gateway)
	@echo "Testing $*..."
	@cd services/$* && npm test 2>/dev/null || pytest

# ============================================
# Code Quality
# ============================================
lint: ## Run linters on all services
	@echo "Running linters..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			echo "Linting $$dir..."; \
			cd "$$dir" && npm run lint && cd ../..; \
		elif [ -f "$$dir/requirements.txt" ]; then \
			echo "Linting $$dir..."; \
			cd "$$dir" && flake8 . && cd ../..; \
		fi \
	done

lint-fix: ## Run linters with auto-fix
	@echo "Running linters with auto-fix..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			cd "$$dir" && npm run lint:fix && cd ../..; \
		fi \
	done

format: ## Format code
	@echo "Formatting code..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			cd "$$dir" && npm run format && cd ../..; \
		elif [ -f "$$dir/requirements.txt" ]; then \
			cd "$$dir" && black . && cd ../..; \
		fi \
	done

typecheck: ## Run type checking
	@echo "Running type checks..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			cd "$$dir" && npm run typecheck && cd ../..; \
		elif [ -f "$$dir/requirements.txt" ]; then \
			cd "$$dir" && mypy . && cd ../..; \
		fi \
	done

# ============================================
# Infrastructure
# ============================================
tf-init: ## Initialize Terraform
	@echo "Initializing Terraform..."
	@cd infrastructure/terraform && terraform init

tf-plan: ## Run Terraform plan
	@echo "Planning Terraform changes..."
	@cd infrastructure/terraform && terraform plan

tf-apply: ## Apply Terraform changes
	@echo "Applying Terraform changes..."
	@cd infrastructure/terraform && terraform apply

tf-destroy: ## Destroy Terraform infrastructure
	@echo "Destroying Terraform infrastructure..."
	@cd infrastructure/terraform && terraform destroy

tf-fmt: ## Format Terraform files
	@cd infrastructure/terraform && terraform fmt -recursive

# ============================================
# Deployment
# ============================================
deploy: ## Deploy all services to GCP
	@echo "Deploying to GCP..."
	@gcloud builds submit --config infrastructure/cloudbuild/cloudbuild.yaml

deploy-staging: ## Deploy to staging environment
	@echo "Deploying to staging..."
	@gcloud builds submit --config infrastructure/cloudbuild/cloudbuild.yaml --substitutions=_ENV=staging

deploy-production: ## Deploy to production environment
	@echo "Deploying to production..."
	@gcloud builds submit --config infrastructure/cloudbuild/cloudbuild.yaml --substitutions=_ENV=production

# ============================================
# Cleanup
# ============================================
clean: ## Clean up build artifacts and temporary files
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.log" -delete
	@docker system prune -f 2>/dev/null || true

distclean: clean ## Clean everything including Docker volumes
	@echo "Deep cleaning..."
	@docker volume prune -f 2>/dev/null || true
	@docker network prune -f 2>/dev/null || true

# ============================================
# Maintenance
# ============================================
update-deps: ## Update all dependencies
	@echo "Updating dependencies..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			cd "$$dir" && npm update && cd ../..; \
		elif [ -f "$$dir/requirements.txt" ]; then \
			cd "$$dir" && pip list --outdated && cd ../..; \
		fi \
	done

security-audit: ## Run security audit
	@echo "Running security audit..."
	@for dir in services/*/; do \
		if [ -f "$$dir/package.json" ]; then \
			cd "$$dir" && npm audit && cd ../..; \
		fi \
	done

# ============================================
# Data Management
# ============================================
init-db: ## Initialize database schema
	@echo "Initializing database..."
	@docker-compose exec postgres psql -U sentilyze -d sentilyze_predictions -f /docker-entrypoint-initdb.d/init.sql

migrate: ## Run database migrations
	@echo "Running migrations..."
	@echo "Implement migration logic here"

seed: ## Seed database with sample data
	@echo "Seeding database..."
	@echo "Implement seeding logic here"

# ============================================
# Monitoring & Debugging
# ============================================
logs-%: ## View logs for specific service (e.g., logs-api-gateway)
	@docker-compose logs -f $*

shell-%: ## Open shell in specific service container (e.g., shell-api-gateway)
	@docker-compose exec $* /bin/sh

psql: ## Open PostgreSQL shell
	@docker-compose exec postgres psql -U sentilyze -d sentilyze_predictions

firestore-cli: ## Open Firestore emulator UI/info
	@echo "Firestore emulator running at http://localhost:8080"
	@echo "Use gcloud CLI for Firestore operations:"
	@echo "  export FIRESTORE_EMULATOR_HOST=localhost:8080"
	@echo "  gcloud firestore documents list --project=${GCP_PROJECT_ID}

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8080/health || echo "API Gateway not responding"

# ============================================
# Utilities
# ============================================
generate-api-docs: ## Generate API documentation
	@echo "Generating API docs..."
	@echo "Implement documentation generation"

generate-terraform-docs: ## Generate Terraform documentation
	@echo "Generating Terraform docs..."
	@cd infrastructure/terraform && terraform-docs markdown . > README.md

check-config: ## Validate environment configuration
	@echo "Checking configuration..."
	@if [ ! -f .env ]; then echo "ERROR: .env file not found. Run 'make setup' first."; exit 1; fi
	@echo "Configuration OK"

# ============================================
# Shortcut Aliases
# ============================================
up: dev ## Alias for dev
start: dev ## Alias for dev
down: dev-stop ## Alias for dev-stop
stop: dev-stop ## Alias for dev-stop
restart: dev-stop dev ## Restart all services
