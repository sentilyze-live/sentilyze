"""Configuration management for Agent OS Core."""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Agent OS Core"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # GCP
    GCP_PROJECT_ID: str = "sentilyze-v5-clean"
    GCP_REGION: str = "us-central1"
    GCP_ZONE: str = "us-central1-a"

    # BigQuery
    BIGQUERY_DATASET: str = "sentilyze_dataset"
    BIGQUERY_LOCATION: str = "US"
    BIGQUERY_EMULATOR_HOST: Optional[str] = None

    # Firestore
    FIRESTORE_PROJECT_ID: str = "sentilyze-v5-clean"
    FIRESTORE_EMULATOR_HOST: Optional[str] = None
    CACHE_TYPE: str = "firestore"

    # Pub/Sub
    PUBSUB_PROJECT_ID: str = "sentilyze-v5-clean"
    PUBSUB_EMULATOR_HOST: Optional[str] = None

    # Moonshot API (Kimi 2.5)
    MOONSHOT_API_KEY: str = Field(default="", description="Moonshot API Key")
    MOONSHOT_BASE_URL: str = "https://api.moonshot.cn/v1"
    MOONSHOT_MODEL: str = "kimi-k2-5"
    MOONSHOT_MAX_TOKENS: int = 2000
    MOONSHOT_TEMPERATURE: float = 0.7
    
    # Agent-Specific Model Configuration (Optimized for Cost & Performance)
    # kimi-k2.5: $0.60/$3.00 - Multimodal, best for complex vision tasks
    # kimi-k2-0905-preview: $0.60/$2.50 - Enhanced coding, JSON, general tasks
    # kimi-k2-thinking: $0.60/$2.50 - Deep reasoning, analysis
    # kimi-k2-turbo-preview: $1.15/$8.00 - High speed (60-100 tokens/sec)
    
    # SCOUT: Market analysis requires deep reasoning
    MOONSHOT_MODEL_SCOUT: str = "kimi-k2-thinking"
    MOONSHOT_MAX_TOKENS_SCOUT: int = 4000
    MOONSHOT_TEMPERATURE_SCOUT: float = 0.6
    
    # ORACLE: Validation and analysis requires deep reasoning
    MOONSHOT_MODEL_ORACLE: str = "kimi-k2-thinking"
    MOONSHOT_MAX_TOKENS_ORACLE: int = 4000
    MOONSHOT_TEMPERATURE_ORACLE: float = 0.6
    
    # SETH: SEO content generation - JSON output, good coding capabilities
    MOONSHOT_MODEL_SETH: str = "kimi-k2-0905-preview"
    MOONSHOT_MAX_TOKENS_SETH: int = 3000
    MOONSHOT_TEMPERATURE_SETH: float = 0.7
    
    # ZARA: Community engagement - fast responses, good reasoning
    MOONSHOT_MODEL_ZARA: str = "kimi-k2-0905-preview"
    MOONSHOT_MAX_TOKENS_ZARA: int = 2000
    MOONSHOT_TEMPERATURE_ZARA: float = 0.8
    
    # ELON: Growth experiments - speed critical for frequent runs
    MOONSHOT_MODEL_ELON: str = "kimi-k2-0905-preview"
    MOONSHOT_MAX_TOKENS_ELON: int = 3000
    MOONSHOT_TEMPERATURE_ELON: float = 0.7

    # CODER: Developer agent - deep reasoning for code analysis
    MOONSHOT_MODEL_CODER: str = "kimi-k2-thinking"
    MOONSHOT_MAX_TOKENS_CODER: int = 6000
    MOONSHOT_TEMPERATURE_CODER: float = 0.3

    # SENTINEL: Anomaly detection - deep reasoning for pattern analysis
    MOONSHOT_MODEL_SENTINEL: str = "kimi-k2-thinking"
    MOONSHOT_MAX_TOKENS_SENTINEL: int = 3000
    MOONSHOT_TEMPERATURE_SENTINEL: float = 0.4

    # ATLAS: Data quality - structured output, cost-effective
    MOONSHOT_MODEL_ATLAS: str = "kimi-k2-0905-preview"
    MOONSHOT_MAX_TOKENS_ATLAS: int = 2000
    MOONSHOT_TEMPERATURE_ATLAS: float = 0.3

    # Higgsfield API
    HIGGSFIELD_API_KEY: str = Field(default="", description="Higgsfield API Key")
    HIGGSFIELD_BASE_URL: str = "https://api.higgsfield.ai/v1"

    # Vertex AI Configuration (Cost-Effective Alternative to Kimi)
    # Use Vertex AI for simpler tasks to reduce costs by 80%
    ENABLE_VERTEX_AI_FOR_AGENTS: bool = True
    VERTEX_AI_PROJECT_ID: str = "sentilyze-v5-clean"
    VERTEX_AI_LOCATION: str = "us-central1"
    VERTEX_AI_MODEL_GEMINI_FLASH: str = "gemini-1.5-flash-001"  # Fast & cheap: $0.35/$1.05 per 1M tokens
    VERTEX_AI_MODEL_GEMINI_PRO: str = "gemini-1.5-pro-001"      # High quality: $3.50/$10.50 per 1M tokens
    
    # Agent Model Selection Strategy (Cost Optimization)
    # Cost-effective routing: Simple tasks → Vertex AI, Complex tasks → Kimi
    USE_VERTEX_FOR_ZARA: bool = True      # Community engagement: Simple, repetitive
    USE_VERTEX_FOR_ELON: bool = True      # Growth experiments: Structured JSON output
    USE_VERTEX_FOR_SETH_METADATA: bool = True  # SEO meta, titles: Simple generation
    USE_KIMI_FOR_SCOUT: bool = True       # Market analysis: Requires deep reasoning
    USE_KIMI_FOR_ORACLE: bool = True      # Validation: Requires statistical rigor
    USE_KIMI_FOR_SETH_LONGFORM: bool = True   # Long content: Requires quality
    
    # Smart Agent Triggering (Skip runs when not needed)
    ENABLE_SMART_TRIGGERS: bool = True
    MARKET_VOLATILITY_THRESHOLD: float = 0.015  # 1.5% - Skip agents if below
    MIN_NEW_DATA_AGE_MINUTES: int = 180  # Skip if no new data in 3 hours
    WEEKEND_REDUCED_MODE: bool = True    # Reduce activity on weekends
    NIGHT_MODE_REDUCTION: bool = True    # Reduce activity 00:00-06:00 UTC
    NIGHT_MODE_HOURS: tuple = (0, 6)     # UTC hours for night mode
    
    # Caching Configuration (Reduce BigQuery costs by 60%)
    ENABLE_BIGQUERY_CACHE: bool = True
    BIGQUERY_CACHE_TTL_MINUTES: int = 60  # Cache BigQuery results for 1 hour
    CACHE_SENTIMENT_DATA: bool = True
    CACHE_PREDICTION_DATA: bool = True
    CACHE_MARKET_DATA: bool = True
    
    # Firestore Optimization
    FIRESTORE_CACHE_TTL_HOURS: int = 24
    FIRESTORE_AUTO_CLEANUP: bool = True  # Auto-delete old records
    FIRESTORE_MAX_RECORD_AGE_DAYS: int = 30  # Keep only 30 days of agent logs
    
    # Pub/Sub Optimization
    PUBSUB_MESSAGE_RETENTION_HOURS: int = 24  # Reduced from 7 days to 24 hours
    PUBSUB_ACK_DEADLINE_SECONDS: int = 60     # Shorter acknowledgment deadline
    
    # Cost Monitoring & Alerts
    ENABLE_COST_TRACKING: bool = True
    DAILY_AI_COST_LIMIT_USD: float = 50.0  # Alert if daily AI cost exceeds $50
    MONTHLY_AI_COST_LIMIT_USD: float = 1000.0  # Alert if monthly cost exceeds $1000
    COST_ALERT_EMAIL: str = "admin@sentilyze.live"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot Token")
    TELEGRAM_CHAT_ID: str = Field(default="", description="Telegram Chat ID")
    ENABLE_TELEGRAM_NOTIFICATIONS: bool = True

    # Feature Flags
    ENABLE_SCOUT: bool = True
    ENABLE_ELON: bool = True
    ENABLE_SETH: bool = True
    ENABLE_ZARA: bool = True
    ENABLE_ORACLE: bool = True
    ENABLE_CODER: bool = True
    ENABLE_SENTINEL: bool = True
    ENABLE_ATLAS: bool = True
    ENABLE_MARIA: bool = True

    # CODER Agent Settings
    CODER_PROJECT_ROOT: str = "/app"
    CODER_REQUIRE_APPROVAL: bool = True

    # SENTINEL Agent Settings
    SENTINEL_INTERVAL_MINUTES: int = 120
    SENTINEL_ZSCORE_THRESHOLD: float = 2.5

    # ATLAS Agent Settings
    ATLAS_INTERVAL_MINUTES: int = 360
    ATLAS_STALENESS_THRESHOLD_MINUTES: int = 180

    # Telegram Rate Limiting
    TELEGRAM_RATE_LIMIT_PER_MINUTE: int = 5
    TELEGRAM_RATE_LIMIT_PER_HOUR: int = 50

    # Autonomous Brainstorming
    ENABLE_BRAINSTORMING: bool = True
    BRAINSTORMING_INTERVAL_HOURS: int = 48  # Every 2 days
    BRAINSTORMING_MAX_PROPOSALS: int = 15
    BRAINSTORMING_AUTO_DISPATCH: bool = True  # Auto-dispatch executable proposals

    # Content Pipeline
    ENABLE_CONTENT_PIPELINE: bool = True
    CONTENT_PLATFORMS: str = "blog,linkedin,twitter,reddit,discord"
    CONTENT_AUTO_PUBLISH_SOCIAL: bool = True  # Auto-publish Twitter/Reddit/Discord
    CONTENT_REQUIRE_REVIEW_BLOG: bool = True  # Blog needs manual review
    CONTENT_REQUIRE_REVIEW_LINKEDIN: bool = True  # LinkedIn needs manual review

    # Autonomous Actions
    ENABLE_AUTONOMOUS_ACTIONS: bool = True
    AUTONOMOUS_ACTION_EXPIRY_HOURS: int = 48  # Pending actions expire after 48h

    # Agent Scheduling (minutes) - FULLY OPTIMIZED FOR COST (70% reduction)
    # OPTIMIZATION: Reduced frequencies by 50-70% with smart triggering
    
    # ZARA: 6 hours → 12 hours (community engagement)
    # Only runs when there are active opportunities (SCOUT detection)
    ZARA_INTERVAL_MINUTES: int = 720
    ZARA_MIN_OPPORTUNITY_SCORE: float = 7.0  # Only run if SCOUT finds high-value opportunities
    
    # SCOUT: 3 hours → 6 hours (market intelligence)
    # Market analysis with intelligent caching
    SCOUT_INTERVAL_MINUTES: int = 360
    SCOUT_MIN_VOLATILITY_THRESHOLD: float = 0.02  # Skip if volatility < 2%
    SCOUT_CACHE_TTL_MINUTES: int = 180  # Cache results for 3 hours
    
    # ORACLE: 6 hours → 12 hours (validation)
    # Only validates when SCOUT detects significant opportunities
    ORACLE_INTERVAL_MINUTES: int = 720
    ORACLE_TRIGGER_MIN_SCORE: float = 7.5  # Only validate high-value opportunities
    ORACLE_MAX_VALIDATIONS_PER_DAY: int = 4  # Max 4 validations daily
    
    # ELON: 12 hours → 24 hours (growth experiments)
    # Daily checks sufficient for growth experiments
    ELON_INTERVAL_MINUTES: int = 1440
    ELON_SKIP_WEEKENDS: bool = True  # Skip weekends for B2B/SaaS focus
    
    # SETH: 24 hours → 48 hours (content creation)
    # Every 2 days is sufficient for quality content
    SETH_INTERVAL_MINUTES: int = 2880
    SETH_MIN_OPPORTUNITY_SCORE: float = 7.0  # Only create content for high-value trends
    SETH_CONTENT_BATCH_SIZE: int = 3  # Batch content creation (3 items per run)

    # Shared Directory
    SHARED_DIR: str = "/shared/agent_os"

    # Data Sources
    ENABLE_SENTILYZE_DATA_ACCESS: bool = True
    SENTIMENT_TABLE: str = "sentiment_analysis"
    PREDICTIONS_TABLE: str = "predictions"
    MARKET_DATA_TABLE: str = "market_data"
    USER_EVENTS_TABLE: str = "user_events"

    # Marketing Goals
    NORTH_STAR_METRIC: str = "mrr_growth"
    TARGET_MRR_GROWTH: float = 0.15  # 15% monthly
    TARGET_ORGANIC_TRAFFIC: int = 10000  # Monthly visitors
    TARGET_CONVERSION_RATE: float = 0.05  # 5%

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    @property
    def enabled_agents(self) -> List[str]:
        """Get list of enabled agents."""
        agents = []
        if self.ENABLE_SCOUT:
            agents.append("scout")
        if self.ENABLE_ELON:
            agents.append("elon")
        if self.ENABLE_SETH:
            agents.append("seth")
        if self.ENABLE_ZARA:
            agents.append("zara")
        if self.ENABLE_ORACLE:
            agents.append("oracle")
        if self.ENABLE_CODER:
            agents.append("coder")
        if self.ENABLE_SENTINEL:
            agents.append("sentinel")
        if self.ENABLE_ATLAS:
            agents.append("atlas")
        if self.ENABLE_MARIA:
            agents.append("maria")
        return agents


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
