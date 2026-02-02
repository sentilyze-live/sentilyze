"""Admin panel configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Admin panel settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    service_name: str = Field(default="admin-panel", alias="SERVICE_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8090, alias="PORT")

    # Database
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_user: str = Field(default="sentilyze", alias="DB_USER")
    db_password: str = Field(default="sentilyze123", alias="DB_PASSWORD")
    db_name: str = Field(default="sentilyze_predictions", alias="DB_NAME")

    # JWT
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Security
    admin_api_key: Optional[str] = Field(default=None, alias="ADMIN_API_KEY")
    cors_origins: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")

    # Google Cloud
    gcp_project_id: str = Field(default="sentilyze-v5-clean", alias="GCP_PROJECT_ID")
    bigquery_dataset: str = Field(default="sentilyze_dataset", alias="BIGQUERY_DATASET")
    bigquery_emulator_host: Optional[str] = Field(default=None, alias="BIGQUERY_EMULATOR_HOST")

    # Services (for health checks)
    api_gateway_url: str = Field(default="http://api-gateway:8080", alias="API_GATEWAY_URL")
    ingestion_url: str = Field(default="http://ingestion:8081", alias="INGESTION_URL")
    sentiment_processor_url: str = Field(
        default="http://sentiment-processor:8082", alias="SENTIMENT_PROCESSOR_URL"
    )
    market_context_url: str = Field(
        default="http://market-context-processor:8083", alias="MARKET_CONTEXT_URL"
    )
    prediction_engine_url: str = Field(
        default="http://prediction-engine:8084", alias="PREDICTION_ENGINE_URL"
    )
    alert_service_url: str = Field(default="http://alert-service:8085", alias="ALERT_SERVICE_URL")
    analytics_engine_url: str = Field(
        default="http://analytics-engine:8086", alias="ANALYTICS_ENGINE_URL"
    )
    tracker_service_url: str = Field(
        default="http://tracker-service:8087", alias="TRACKER_SERVICE_URL"
    )

    # Feature Flags
    enable_user_management: bool = Field(default=True, alias="ENABLE_USER_MANAGEMENT")
    enable_service_control: bool = Field(default=True, alias="ENABLE_SERVICE_CONTROL")
    enable_analytics_dashboard: bool = Field(default=True, alias="ENABLE_ANALYTICS_DASHBOARD")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = {"development", "staging", "production", "test"}
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    @property
    def database_url(self) -> str:
        """Get async database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL (for Alembic migrations)."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test."""
        return self.environment == "test"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def service_urls(self) -> dict[str, str]:
        """Get all service URLs as dict."""
        return {
            "api-gateway": self.api_gateway_url,
            "ingestion": self.ingestion_url,
            "sentiment-processor": self.sentiment_processor_url,
            "market-context-processor": self.market_context_url,
            "prediction-engine": self.prediction_engine_url,
            "alert-service": self.alert_service_url,
            "analytics-engine": self.analytics_engine_url,
            "tracker-service": self.tracker_service_url,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton)."""
    return Settings()
