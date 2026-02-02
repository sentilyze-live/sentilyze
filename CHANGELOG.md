# Changelog

All notable changes to the Sentilyze project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial unified platform implementation
- Comprehensive deployment scripts for GCP and local environments
- BigQuery setup utility with predefined schemas
- Pub/Sub setup utility with topic and subscription management
- Database migration system with rollback support
- Health check script for all services
- Secret management utility
- Data retention policy runner
- Load testing tool
- Quick start guide and contribution guidelines

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [1.0.0] - 2026-01-31

### Added
- Unified sentiment analysis platform architecture
- RESTful API for real-time sentiment analysis
- Background worker service for batch processing
- Job scheduler for periodic tasks
- Multi-service support (API, Worker, Scheduler)
- Docker containerization for all services
- Cloud Run deployment support
- BigQuery integration for data warehousing
- Pub/Sub messaging infrastructure
- PostgreSQL database with migration system
- Redis caching layer
- Secret management via Google Secret Manager
- Comprehensive monitoring and health checks
- Data retention policies
- Load testing capabilities

### API Features
- Real-time sentiment analysis endpoint
- Batch processing endpoint
- Job status tracking
- Health check endpoint
- API documentation (OpenAPI/Swagger)

### Deployment
- GCP Cloud Run deployment scripts
- Local Docker Compose setup
- Automated CI/CD pipeline configuration
- Infrastructure as Code (IaC) support

### Documentation
- Comprehensive README
- Quick start guide
- API documentation
- Contributing guidelines
- Deployment guides

### Infrastructure
- BigQuery datasets and tables
- Pub/Sub topics and subscriptions
- Service accounts and IAM permissions
- Cloud Storage buckets
- Secret Manager configuration

[Unreleased]: https://github.com/your-org/sentilyze/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/sentilyze/releases/tag/v1.0.0
