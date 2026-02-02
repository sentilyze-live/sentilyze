"""Configuration management using Pydantic Settings.

This package provides centralized configuration for all Sentilyze microservices.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings for all Sentilyze services.

    Unified configuration supporting crypto, gold, and all microservices.
    
    NOTE:
    - Many settings are optional so services that don't use specific features
      can still start without providing unrelated env vars.
    - Service-specific modules should validate required config at point-of-use.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =============================================================================
    # Core / General Settings
    # =============================================================================
    service_name: str = Field(default="sentilyze", alias="SERVICE_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # API Gateway specific
    app_name: str = Field(default="Sentilyze API Gateway", alias="APP_NAME")
    app_version: str = Field(default="4.0.0", alias="APP_VERSION")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Google Cloud
    google_cloud_project: Optional[str] = Field(
        default=None,
        alias="GOOGLE_CLOUD_PROJECT",
    )
    google_application_credentials: Optional[str] = Field(
        default=None,
        alias="GOOGLE_APPLICATION_CREDENTIALS",
    )

    # Pub/Sub
    pubsub_project_id: str = Field(alias="PUBSUB_PROJECT_ID")
    pubsub_emulator_host: Optional[str] = Field(
        default=None,
        alias="PUBSUB_EMULATOR_HOST",
    )

    # BigQuery (single unified dataset)
    bigquery_dataset: str = Field(default="sentilyze_dataset", alias="BIGQUERY_DATASET")
    bigquery_emulator_host: Optional[str] = Field(
        default=None,
        alias="BIGQUERY_EMULATOR_HOST",
    )
    bigquery_max_bytes_billed: int = Field(
        default=100_000_000_000,  # 100 GB default
        alias="BIGQUERY_MAX_BYTES_BILLED",
        description="Maximum bytes billed per query to prevent cost overruns",
    )

    # Redis
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    # Cache Configuration (Redis vs Firestore) - Firestore is default for GCP
    cache_type: str = Field(
        default="firestore",
        alias="CACHE_TYPE",
        description="Cache backend: 'redis' or 'firestore' (Firestore recommended for GCP)",
    )
    firestore_project_id: Optional[str] = Field(
        default=None,
        alias="FIRESTORE_PROJECT_ID",
        description="Firestore project ID (defaults to GOOGLE_CLOUD_PROJECT)",
    )

    # API Gateway
    jwt_secret: Optional[str] = Field(default=None, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")

    # Ingestion - Crypto
    reddit_client_id: Optional[str] = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(
        default=None,
        alias="REDDIT_CLIENT_SECRET",
    )
    reddit_user_agent: str = Field(default="Sentilyze/4.0", alias="REDDIT_USER_AGENT")
    binance_api_key: Optional[str] = Field(default=None, alias="BINANCE_API_KEY")
    binance_api_secret: Optional[str] = Field(default=None, alias="BINANCE_API_SECRET")
    coingecko_api_key: Optional[str] = Field(default=None, alias="COINGECKO_API_KEY")
    finnhub_api_key: Optional[str] = Field(default=None, alias="FINNHUB_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
    lunarcrush_api_key: Optional[str] = Field(default=None, alias="LUNARCRUSH_API_KEY")
    cryptopanic_api_key: Optional[str] = Field(default=None, alias="CRYPTOPANIC_API_KEY")
    santiment_api_key: Optional[str] = Field(default=None, alias="SANTIMENT_API_KEY")
    fred_api_key: Optional[str] = Field(default=None, alias="FRED_API_KEY")

    # Ingestion - Gold/Metals
    goldapi_api_key: Optional[str] = Field(default=None, alias="GOLDAPI_API_KEY")
    metals_api_key: Optional[str] = Field(default=None, alias="METALS_API_KEY")
    twelve_data_api_key: Optional[str] = Field(default=None, alias="TWELVE_DATA_API_KEY")
    eodhd_api_key: Optional[str] = Field(default=None, alias="EODHD_API_KEY")
    
    ingestion_admin_api_key: Optional[str] = Field(
        default=None,
        alias="INGESTION_ADMIN_API_KEY",
    )
    cors_origins: Optional[list[str]] = Field(default=None, alias="CORS_ORIGINS")
    
    # Ingestion scheduler intervals
    scheduler_collection_interval: int = Field(default=300, alias="SCHEDULER_COLLECTION_INTERVAL")
    scheduler_reddit_interval: int = Field(default=600, alias="SCHEDULER_REDDIT_INTERVAL")
    scheduler_rss_interval: int = Field(default=300, alias="SCHEDULER_RSS_INTERVAL")
    scheduler_binance_interval: int = Field(default=60, alias="SCHEDULER_BINANCE_INTERVAL")
    scheduler_goldapi_interval: int = Field(default=60, alias="SCHEDULER_GOLDAPI_INTERVAL")
    scheduler_finnhub_interval: int = Field(default=300, alias="SCHEDULER_FINNHUB_INTERVAL")
    scheduler_turkish_interval: int = Field(default=300, alias="SCHEDULER_TURKISH_INTERVAL")
    scheduler_lunarcrush_interval: int = Field(default=300, alias="SCHEDULER_LUNARCRUSH_INTERVAL")
    scheduler_cryptopanic_interval: int = Field(default=300, alias="SCHEDULER_CRYPTOPANIC_INTERVAL")
    scheduler_santiment_interval: int = Field(default=300, alias="SCHEDULER_SANTIMENT_INTERVAL")
    scheduler_fred_interval: int = Field(default=300, alias="SCHEDULER_FRED_INTERVAL")
    
    # GoldAPI/Finnhub settings
    goldapi_symbols: Optional[list[str]] = Field(default=None, alias="GOLDAPI_SYMBOLS")
    goldapi_currencies: Optional[list[str]] = Field(default=None, alias="GOLDAPI_CURRENCIES")
    goldapi_interval: int = Field(default=60, alias="GOLDAPI_INTERVAL")
    finnhub_symbols: Optional[list[str]] = Field(default=None, alias="FINNHUB_SYMBOLS")
    finnhub_interval: int = Field(default=300, alias="FINNHUB_INTERVAL")
    lunarcrush_symbols: Optional[list[str]] = Field(default=None, alias="LUNARCRUSH_SYMBOLS")
    lunarcrush_interval: int = Field(default=300, alias="LUNARCRUSH_INTERVAL")
    cryptopanic_currencies: Optional[list[str]] = Field(default=None, alias="CRYPTOPANIC_CURRENCIES")
    cryptopanic_filter: Optional[str] = Field(default=None, alias="CRYPTOPANIC_FILTER")
    cryptopanic_interval: int = Field(default=300, alias="CRYPTOPANIC_INTERVAL")
    santiment_assets: Optional[list[str]] = Field(default=None, alias="SANTIMENT_ASSETS")
    santiment_metrics: Optional[list[str]] = Field(default=None, alias="SANTIMENT_METRICS")
    santiment_interval: int = Field(default=300, alias="SANTIMENT_INTERVAL")
    fred_series: Optional[dict] = Field(default=None, alias="FRED_SERIES")
    fred_interval: int = Field(default=300, alias="FRED_INTERVAL")
    
    # Circuit breaker settings (ingestion specific)
    circuit_failure_threshold: int = Field(default=5, alias="CIRCUIT_FAILURE_THRESHOLD")
    circuit_recovery_timeout: int = Field(default=60, alias="CIRCUIT_RECOVERY_TIMEOUT")
    circuit_expected_exception: str = Field(default="ExternalServiceError", alias="CIRCUIT_EXPECTED_EXCEPTION")

    # Sentiment Processor
    vertex_ai_project_id: Optional[str] = Field(default=None, alias="VERTEX_AI_PROJECT_ID")
    vertex_ai_location: str = Field(default="us-central1", alias="VERTEX_AI_LOCATION")
    gemini_model: str = Field(default="gemini-1.5-flash-001", alias="GEMINI_MODEL")
    sentiment_cache_ttl: int = Field(default=3600, alias="SENTIMENT_CACHE_TTL")
    gemini_max_concurrency: int = Field(default=5, alias="GEMINI_MAX_CONCURRENCY")
    gemini_queue_timeout_seconds: float = Field(
        default=1.0,
        alias="GEMINI_QUEUE_TIMEOUT_SECONDS",
    )
    gemini_rpm_limit: Optional[int] = Field(default=None, alias="GEMINI_RPM_LIMIT")
    gemini_retry_max_attempts: int = Field(default=4, alias="GEMINI_RETRY_MAX_ATTEMPTS")
    gemini_daily_limit: int = Field(
        default=500,
        alias="GEMINI_DAILY_LIMIT",
        description="Daily request limit for Vertex AI to prevent cost overruns",
    )

    # Sentiment Processor (Lite / Fallback)
    sentiment_lite_mode: bool = Field(default=False, alias="SENTIMENT_LITE_MODE")
    sentiment_lite_max_chars: int = Field(default=160, alias="SENTIMENT_LITE_MAX_CHARS")

    # =============================================================================
    # Alert Service Settings
    # =============================================================================
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_ids: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_IDS")
    telegram_rate_limit_per_minute: int = Field(default=20, alias="TELEGRAM_RATE_LIMIT_PER_MINUTE")
    
    alert_webhook_url: Optional[str] = Field(default=None, alias="ALERT_WEBHOOK_URL")
    webhook_secret: Optional[str] = Field(default=None, alias="WEBHOOK_SECRET")
    webhook_timeout: int = Field(default=10, alias="WEBHOOK_TIMEOUT")
    
    alert_default_channels: str = Field(
        default="telegram",
        alias="ALERT_DEFAULT_CHANNELS",
        description="Comma-separated channels (telegram, webhook)",
    )
    alert_telegram_chat_ids: Optional[str] = Field(
        default=None,
        alias="ALERT_TELEGRAM_CHAT_IDS",
        description="Comma-separated Telegram chat IDs for default routing",
    )
    
    # Alert feature flags
    enable_telegram: bool = Field(default=True, alias="ENABLE_TELEGRAM")
    enable_webhook: bool = Field(default=False, alias="ENABLE_WEBHOOK")
    enable_email: bool = Field(default=False, alias="ENABLE_EMAIL")
    enable_slack: bool = Field(default=False, alias="ENABLE_SLACK")
    enable_rate_limiting: bool = Field(default=True, alias="ENABLE_RATE_LIMITING")
    enable_idempotency: bool = Field(default=True, alias="ENABLE_IDEMPOTENCY")
    
    # Email settings
    email_smtp_host: Optional[str] = Field(default=None, alias="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, alias="EMAIL_SMTP_PORT")
    email_username: Optional[str] = Field(default=None, alias="EMAIL_USERNAME")
    email_password: Optional[str] = Field(default=None, alias="EMAIL_PASSWORD")
    email_from: Optional[str] = Field(default=None, alias="EMAIL_FROM")
    
    # Slack settings
    slack_webhook_url: Optional[str] = Field(default=None, alias="SLACK_WEBHOOK_URL")
    slack_channel: Optional[str] = Field(default=None, alias="SLACK_CHANNEL")
    
    # Alert thresholds and rate limiting
    alert_negative_score_threshold: float = Field(
        default=-0.2,
        alias="ALERT_NEGATIVE_SCORE_THRESHOLD",
    )
    alert_positive_score_threshold: float = Field(
        default=0.7,
        alias="ALERT_POSITIVE_SCORE_THRESHOLD",
    )
    alert_min_confidence: float = Field(
        default=0.6,
        alias="ALERT_MIN_CONFIDENCE",
    )
    alert_cooldown_seconds: int = Field(
        default=900,
        alias="ALERT_COOLDOWN_SECONDS",
        description="Cooldown per symbol+alert_type to reduce noise",
    )
    rate_limit_requests_per_minute: int = Field(default=30, alias="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_cooldown_seconds: int = Field(default=60, alias="RATE_LIMIT_COOLDOWN_SECONDS")
    cache_ttl_seconds: int = Field(default=604800, alias="CACHE_TTL_SECONDS")  # 7 days for idempotency

    # Observability
    otel_exporter_otlp_endpoint: Optional[str] = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_service_name: str = Field(default="sentilyze", alias="OTEL_SERVICE_NAME")

    # =============================================================================
    # Prediction Engine Settings
    # =============================================================================
    # ML Model settings
    ml_model_estimators: int = Field(default=50, alias="ML_MODEL_ESTIMATORS")
    ml_model_max_depth: int = Field(default=10, alias="ML_MODEL_MAX_DEPTH")
    ml_model_random_state: int = Field(default=42, alias="ML_MODEL_RANDOM_STATE")
    
    # Technical indicator settings
    rsi_period: int = Field(default=14, alias="RSI_PERIOD")
    macd_fast: int = Field(default=12, alias="MACD_FAST")
    macd_slow: int = Field(default=26, alias="MACD_SLOW")
    macd_signal: int = Field(default=9, alias="MACD_SIGNAL")
    bb_period: int = Field(default=20, alias="BB_PERIOD")
    bb_std_dev: float = Field(default=2.0, alias="BB_STD_DEV")
    ema_short: int = Field(default=9, alias="EMA_SHORT")
    ema_medium: int = Field(default=21, alias="EMA_MEDIUM")
    ema_long: int = Field(default=50, alias="EMA_LONG")
    
    # Prediction settings
    min_history_hours: int = Field(default=24, alias="MIN_HISTORY_HOURS")
    min_confidence_score: int = Field(default=30, alias="MIN_CONFIDENCE_SCORE")
    max_confidence_score: int = Field(default=95, alias="MAX_CONFIDENCE_SCORE")
    
    # Prediction feature flags
    enable_ml_predictions: bool = Field(default=True, alias="ENABLE_ML_PREDICTIONS")
    enable_technical_analysis: bool = Field(default=True, alias="ENABLE_TECHNICAL_ANALYSIS")
    enable_crypto_predictions: bool = Field(default=True, alias="ENABLE_CRYPTO_PREDICTIONS")
    enable_gold_predictions: bool = Field(default=True, alias="ENABLE_GOLD_PREDICTIONS")
    enable_auto_retraining: bool = Field(default=False, alias="ENABLE_AUTO_RETRAINING")
    
    # =============================================================================
    # Analytics Engine Settings
    # =============================================================================
    # Correlation settings
    correlation_min_data_points: int = Field(default=30, alias="CORRELATION_MIN_DATA_POINTS")
    correlation_max_lag_hours: int = Field(default=48, alias="CORRELATION_MAX_LAG_HOURS")
    
    # Granger causality settings
    granger_max_lag_hours: int = Field(default=24, alias="GRANGER_MAX_LAG_HOURS")
    granger_significance_level: float = Field(default=0.05, alias="GRANGER_SIGNIFICANCE_LEVEL")
    
    # Backtesting settings
    backtest_default_days: int = Field(default=30, alias="BACKTEST_DEFAULT_DAYS")
    backtest_max_days: int = Field(default=365, alias="BACKTEST_MAX_DAYS")
    backtest_min_trades: int = Field(default=10, alias="BACKTEST_MIN_TRADES")
    
    # Materialization settings
    materialize_default_hours: int = Field(default=24, alias="MATERIALIZE_DEFAULT_HOURS")
    materialize_max_hours: int = Field(default=168, alias="MATERIALIZE_MAX_HOURS")
    
    # Analytics feature flags
    enable_correlation_analysis: bool = Field(default=True, alias="ENABLE_CORRELATION_ANALYSIS")
    enable_granger_causality: bool = Field(default=True, alias="ENABLE_GRANGER_CAUSALITY")
    enable_backtesting: bool = Field(default=True, alias="ENABLE_BACKTESTING")
    enable_sentiment_aggregation: bool = Field(default=True, alias="ENABLE_SENTIMENT_AGGREGATION")
    enable_materialization: bool = Field(default=True, alias="ENABLE_MATERIALIZATION")
    enable_crypto_analytics: bool = Field(default=True, alias="ENABLE_CRYPTO_ANALYTICS")
    enable_gold_analytics: bool = Field(default=True, alias="ENABLE_GOLD_ANALYTICS")
    
    # =============================================================================
    # Tracker Service Settings
    # =============================================================================
    # AI Analysis settings
    ai_analysis_threshold_direction_error: bool = Field(default=True, alias="AI_ANALYSIS_THRESHOLD_DIRECTION_ERROR")
    ai_analysis_threshold_price_diff: float = Field(default=5.0, alias="AI_ANALYSIS_THRESHOLD_PRICE_DIFF")
    ai_analysis_timeout_seconds: float = Field(default=10.0, alias="AI_ANALYSIS_TIMEOUT_SECONDS")
    ai_model: str = Field(default="gemini-1.5-flash-001", alias="AI_MODEL")
    
    # Tracking settings
    tracking_batch_size: int = Field(default=100, alias="TRACKING_BATCH_SIZE")
    tracking_interval_minutes: int = Field(default=30, alias="TRACKING_INTERVAL_MINUTES")
    price_tolerance_flat: float = Field(default=0.5, alias="PRICE_TOLERANCE_FLAT")
    
    # Success thresholds
    success_threshold_excellent: float = Field(default=2.0, alias="SUCCESS_THRESHOLD_EXCELLENT")
    success_threshold_good: float = Field(default=5.0, alias="SUCCESS_THRESHOLD_GOOD")
    
    # Tracker feature flags
    enable_ai_analysis: bool = Field(default=True, alias="ENABLE_AI_ANALYSIS")
    enable_auto_tracking: bool = Field(default=True, alias="ENABLE_AUTO_TRACKING")
    enable_learning_insights: bool = Field(default=True, alias="ENABLE_LEARNING_INSIGHTS")
    enable_crypto_tracking: bool = Field(default=True, alias="ENABLE_CRYPTO_TRACKING")
    enable_gold_tracking: bool = Field(default=True, alias="ENABLE_GOLD_TRACKING")
    
    # =============================================================================
    # Market Context Processor Settings
    # =============================================================================
    # Regime detection settings
    regime_lookback_period: int = Field(default=200, alias="REGIME_LOOKBACK_PERIOD")
    regime_rsi_period: int = Field(default=14, alias="REGIME_RSI_PERIOD")
    regime_sma_fast: int = Field(default=50, alias="REGIME_SMA_FAST")
    regime_sma_slow: int = Field(default=200, alias="REGIME_SMA_SLOW")
    regime_ema_period: int = Field(default=20, alias="REGIME_EMA_PERIOD")
    regime_adx_period: int = Field(default=14, alias="REGIME_ADX_PERIOD")
    regime_atr_period: int = Field(default=14, alias="REGIME_ATR_PERIOD")
    
    # Anomaly detection settings
    anomaly_price_move_threshold: float = Field(default=1.5, alias="ANOMALY_PRICE_MOVE_THRESHOLD")
    anomaly_volatility_threshold: float = Field(default=2.0, alias="ANOMALY_VOLATILITY_THRESHOLD")
    anomaly_volume_threshold: float = Field(default=3.0, alias="ANOMALY_VOLUME_THRESHOLD")
    anomaly_lookback_periods: int = Field(default=20, alias="ANOMALY_LOOKBACK_PERIODS")
    
    # Correlation analysis settings
    correlation_min_sample_size: int = Field(default=30, alias="CORRELATION_MIN_SAMPLE_SIZE")
    correlation_default_period_days: int = Field(default=30, alias="CORRELATION_DEFAULT_PERIOD_DAYS")
    correlation_rolling_window: int = Field(default=10, alias="CORRELATION_ROLLING_WINDOW")
    
    # Market context feature flags
    enable_anomaly_detection: bool = Field(default=True, alias="ENABLE_ANOMALY_DETECTION")
    enable_crypto_markets: bool = Field(default=True, alias="ENABLE_CRYPTO_MARKETS")
    enable_gold_markets: bool = Field(default=True, alias="ENABLE_GOLD_MARKETS")
    
    # =============================================================================
    # API Gateway Settings
    # =============================================================================
    # Security
    admin_api_key: Optional[str] = Field(default=None, alias="ADMIN_API_KEY")
    admin_secret_key: Optional[str] = Field(default=None, alias="ADMIN_SECRET_KEY")
    api_key_header: str = Field(default="X-API-Key", alias="API_KEY_HEADER")
    gold_api_key: Optional[str] = Field(default=None, alias="GOLD_API_KEY")
    crypto_api_key: Optional[str] = Field(default=None, alias="CRYPTO_API_KEY")
    ws_secret: Optional[str] = Field(default=None, alias="WS_SECRET")
    
    # CORS
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    cors_credentials: bool = Field(default=False, alias="CORS_CREDENTIALS")
    
    # Redis settings (API Gateway specific)
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_ssl: bool = Field(default=False, alias="REDIS_SSL")
    
    # External Services
    goldapi_url: Optional[str] = Field(default=None, alias="GOLDAPI_URL")
    crypto_api_url: Optional[str] = Field(default=None, alias="CRYPTO_API_URL")
    
    # Trusted hosts
    trusted_hosts: list[str] = Field(default_factory=lambda: ["*"], alias="TRUSTED_HOSTS")
    
    # API Gateway feature flags
    feature_crypto_routes: bool = Field(default=True, alias="FEATURE_CRYPTO_ROUTES")
    feature_gold_routes: bool = Field(default=True, alias="FEATURE_GOLD_ROUTES")
    feature_sentiment_routes: bool = Field(default=True, alias="FEATURE_SENTIMENT_ROUTES")
    feature_analytics_routes: bool = Field(default=True, alias="FEATURE_ANALYTICS_ROUTES")
    feature_admin_routes: bool = Field(default=True, alias="FEATURE_ADMIN_ROUTES")
    feature_websocket: bool = Field(default=True, alias="FEATURE_WEBSOCKET")
    
    # =============================================================================
    # Sentiment Processor Settings
    # =============================================================================
    enable_alerts: bool = Field(default=True, alias="ENABLE_ALERTS")
    enable_crypto_analysis: bool = Field(default=True, alias="ENABLE_CRYPTO_ANALYSIS")
    enable_gold_analysis: bool = Field(default=True, alias="ENABLE_GOLD_ANALYSIS")
    enable_cot_framework: bool = Field(default=True, alias="ENABLE_COT_FRAMEWORK")
    
    # =============================================================================
    # Feature Flags - Crypto Market
    # =============================================================================
    enable_crypto_market: bool = Field(
        default=True,
        alias="ENABLE_CRYPTO_MARKET",
        description="Enable crypto market features",
    )
    enable_reddit_collector: bool = Field(default=True, alias="ENABLE_REDDIT_COLLECTOR")
    enable_rss_collector: bool = Field(default=True, alias="ENABLE_RSS_COLLECTOR")
    enable_binance_collector: bool = Field(default=True, alias="ENABLE_BINANCE_COLLECTOR")
    enable_coingecko_collector: bool = Field(default=True, alias="ENABLE_COINGECKO_COLLECTOR")
    enable_finnhub_crypto: bool = Field(default=True, alias="ENABLE_FINNHUB_CRYPTO")
    enable_crypto_alerts: bool = Field(default=True, alias="ENABLE_CRYPTO_ALERTS")
    enable_crypto_sentiment: bool = Field(default=True, alias="ENABLE_CRYPTO_SENTIMENT")
    
    # Ingestion feature flags
    enable_turkish_scrapers: bool = Field(default=False, alias="ENABLE_TURKISH_SCRAPERS")
    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    enable_finnhub_collector: bool = Field(default=False, alias="ENABLE_FINNHUB_COLLECTOR")
    enable_lunarcrush_collector: bool = Field(default=True, alias="ENABLE_LUNARCRUSH_COLLECTOR")
    enable_cryptopanic_collector: bool = Field(default=True, alias="ENABLE_CRYPTOPANIC_COLLECTOR")
    enable_santiment_collector: bool = Field(default=True, alias="ENABLE_SANTIMENT_COLLECTOR")
    enable_fred_collector: bool = Field(default=True, alias="ENABLE_FRED_COLLECTOR")

    # =============================================================================
    # Feature Flags - Gold/Metals Market
    # =============================================================================
    enable_gold_market: bool = Field(
        default=True,
        alias="ENABLE_GOLD_MARKET",
        description="Enable gold/precious metals market features",
    )
    enable_goldapi_collector: bool = Field(default=True, alias="ENABLE_GOLDAPI_COLLECTOR")
    enable_metals_api_collector: bool = Field(default=True, alias="ENABLE_METALS_API_COLLECTOR")
    enable_twelve_data_collector: bool = Field(default=True, alias="ENABLE_TWELVE_DATA_COLLECTOR")
    enable_alpha_vantage_metals: bool = Field(default=True, alias="ENABLE_ALPHA_VANTAGE_METALS")
    enable_gold_alerts: bool = Field(default=True, alias="ENABLE_GOLD_ALERTS")
    enable_gold_sentiment: bool = Field(default=True, alias="ENABLE_GOLD_SENTIMENT")
    enable_macro_analysis: bool = Field(default=True, alias="ENABLE_MACRO_ANALYSIS")
    enable_regime_detection: bool = Field(default=True, alias="ENABLE_REGIME_DETECTION")

    # =============================================================================
    # Circuit Breaker Settings
    # =============================================================================
    circuit_breaker_enabled: bool = Field(
        default=True,
        alias="CIRCUIT_BREAKER_ENABLED",
        description="Enable circuit breaker pattern for external APIs",
    )
    circuit_breaker_fail_max: int = Field(default=5, alias="CIRCUIT_BREAKER_FAIL_MAX")
    circuit_breaker_reset_timeout: int = Field(default=60, alias="CIRCUIT_BREAKER_RESET_TIMEOUT")
    circuit_breaker_half_open_max: int = Field(default=3, alias="CIRCUIT_BREAKER_HALF_OPEN_MAX")

    # =============================================================================
    # Data Retention Settings
    # =============================================================================
    data_retention_bronze_days: int = Field(default=180, alias="DATA_RETENTION_BRONZE_DAYS")
    data_retention_silver_days: int = Field(default=365, alias="DATA_RETENTION_SILVER_DAYS")
    data_retention_archive_enabled: bool = Field(default=True, alias="DATA_RETENTION_ARCHIVE_ENABLED")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        allowed = {"development", "staging", "production"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v_lower

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def use_emulators(self) -> bool:
        """Check if using local emulators."""
        return self.is_development and (
            self.pubsub_emulator_host is not None or self.bigquery_emulator_host is not None
        )



    @property
    def active_markets(self) -> list[str]:
        """Get list of active markets based on feature flags."""
        markets = []
        if self.enable_crypto_market:
            markets.append("crypto")
        if self.enable_gold_market:
            markets.append("gold")
        return markets

    def get_allowed_origins_list(self) -> list[str]:
        """Get allowed origins as list from comma-separated string."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()] or ["*"]

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        protocol = "rediss" if self.redis_ssl else "redis"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Scraper Configuration
    scraper_cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        alias="SCRAPER_CACHE_TTL_SECONDS",
        description="How long to show cached data when scrapers fail",
    )
    basic_auth_user: Optional[str] = Field(
        default=None,
        alias="BASIC_AUTH_USER",
    )
    basic_auth_pass: Optional[str] = Field(
        default=None,
        alias="BASIC_AUTH_PASS",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
