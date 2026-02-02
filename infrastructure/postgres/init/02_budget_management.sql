-- ============================================
-- Budget Management & Cost Tracking Schema
-- ============================================
-- Created: 2026-01-31
-- Purpose: Track system costs, manage budgets, and optimize spending

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. Budget Configuration Table
-- ============================================
-- Stores budget tier configurations and limits
CREATE TABLE IF NOT EXISTS budget_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    tier_name VARCHAR(20) NOT NULL CHECK (tier_name IN ('minimal', 'basic', 'standard', 'premium', 'custom')),
    monthly_budget_usd DECIMAL(10, 2) NOT NULL CHECK (monthly_budget_usd >= 0),
    config_json JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    CONSTRAINT unique_active_config_per_tenant UNIQUE(tenant_id, is_active) WHERE is_active = TRUE
);

-- Index for fast tenant lookups
CREATE INDEX IF NOT EXISTS idx_budget_configs_tenant ON budget_configs(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_budget_configs_tier ON budget_configs(tier_name);
CREATE INDEX IF NOT EXISTS idx_budget_configs_effective ON budget_configs(effective_from, effective_until);

-- Comment on table
COMMENT ON TABLE budget_configs IS 'Budget tier configurations with feature flags and limits';
COMMENT ON COLUMN budget_configs.config_json IS 'JSON configuration: collector intervals, feature flags, quotas';
COMMENT ON COLUMN budget_configs.tier_name IS 'Budget tier: minimal, basic, standard, premium, or custom';

-- ============================================
-- 2. Cost Tracking Table
-- ============================================
-- Records daily cost metrics per service
CREATE TABLE IF NOT EXISTS cost_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    date DATE NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    service_category VARCHAR(30) NOT NULL CHECK (service_category IN ('api', 'compute', 'storage', 'ml', 'network', 'other')),
    cost_type VARCHAR(30) NOT NULL CHECK (cost_type IN ('api_call', 'compute_time', 'storage_bytes', 'ml_request', 'egress', 'query_bytes', 'message_count')),
    usage_count INTEGER DEFAULT 0 CHECK (usage_count >= 0),
    usage_amount DECIMAL(18, 4) DEFAULT 0 CHECK (usage_amount >= 0),
    estimated_cost_usd DECIMAL(10, 6) DEFAULT 0 CHECK (estimated_cost_usd >= 0),
    actual_cost_usd DECIMAL(10, 6),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_cost_per_day_service_type UNIQUE(tenant_id, date, service_name, cost_type)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_cost_tracking_tenant_date ON cost_tracking(tenant_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_service ON cost_tracking(service_name, service_category);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_date_category ON cost_tracking(date DESC, service_category);

-- Comment on table
COMMENT ON TABLE cost_tracking IS 'Daily cost tracking per service and cost type';
COMMENT ON COLUMN cost_tracking.usage_amount IS 'Numeric usage (e.g., bytes, seconds, count)';
COMMENT ON COLUMN cost_tracking.estimated_cost_usd IS 'Estimated cost based on usage and pricing model';
COMMENT ON COLUMN cost_tracking.actual_cost_usd IS 'Actual cost from billing API (if available)';

-- ============================================
-- 3. Budget Alerts Table
-- ============================================
-- Stores budget threshold alerts and warnings
CREATE TABLE IF NOT EXISTS budget_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    alert_type VARCHAR(30) NOT NULL CHECK (alert_type IN ('budget_warning', 'budget_exceeded', 'service_expensive', 'quota_reached', 'anomaly_detected')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    threshold_percent DECIMAL(5, 2),
    current_spend_usd DECIMAL(10, 2),
    budget_limit_usd DECIMAL(10, 2),
    message TEXT NOT NULL,
    details JSONB,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for alert queries
CREATE INDEX IF NOT EXISTS idx_budget_alerts_tenant ON budget_alerts(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_budget_alerts_unacknowledged ON budget_alerts(tenant_id, is_acknowledged) WHERE is_acknowledged = FALSE;
CREATE INDEX IF NOT EXISTS idx_budget_alerts_severity ON budget_alerts(severity, created_at DESC);

-- Comment on table
COMMENT ON TABLE budget_alerts IS 'Budget alerts and warnings for overspending or quota limits';
COMMENT ON COLUMN budget_alerts.threshold_percent IS 'Budget threshold percentage that triggered this alert';
COMMENT ON COLUMN budget_alerts.details IS 'Additional context (service breakdown, recommendations)';

-- ============================================
-- 4. Service Quotas Table
-- ============================================
-- Tracks usage quotas per service
CREATE TABLE IF NOT EXISTS service_quotas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    quota_type VARCHAR(30) NOT NULL CHECK (quota_type IN ('daily_requests', 'monthly_requests', 'concurrent_connections', 'storage_gb', 'compute_hours')),
    quota_limit INTEGER NOT NULL CHECK (quota_limit > 0),
    current_usage INTEGER DEFAULT 0 CHECK (current_usage >= 0),
    reset_period VARCHAR(20) NOT NULL CHECK (reset_period IN ('hourly', 'daily', 'monthly', 'never')),
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    next_reset TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_quota_per_service_type UNIQUE(tenant_id, service_name, quota_type)
);

-- Indexes for quota checks
CREATE INDEX IF NOT EXISTS idx_service_quotas_tenant_service ON service_quotas(tenant_id, service_name);
CREATE INDEX IF NOT EXISTS idx_service_quotas_active ON service_quotas(is_active, tenant_id);
CREATE INDEX IF NOT EXISTS idx_service_quotas_reset ON service_quotas(reset_period, last_reset);

-- Comment on table
COMMENT ON TABLE service_quotas IS 'Service-level usage quotas and limits';
COMMENT ON COLUMN service_quotas.current_usage IS 'Current usage count in the period';
COMMENT ON COLUMN service_quotas.next_reset IS 'Calculated timestamp for next quota reset';

-- ============================================
-- 5. Daily Cost Reports (Materialized Summary)
-- ============================================
-- Pre-aggregated daily cost reports
CREATE TABLE IF NOT EXISTS cost_reports_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    report_date DATE NOT NULL,
    total_cost_usd DECIMAL(10, 2) NOT NULL CHECK (total_cost_usd >= 0),
    api_costs_usd DECIMAL(10, 2) DEFAULT 0 CHECK (api_costs_usd >= 0),
    compute_costs_usd DECIMAL(10, 2) DEFAULT 0 CHECK (compute_costs_usd >= 0),
    storage_costs_usd DECIMAL(10, 2) DEFAULT 0 CHECK (storage_costs_usd >= 0),
    ml_costs_usd DECIMAL(10, 2) DEFAULT 0 CHECK (ml_costs_usd >= 0),
    network_costs_usd DECIMAL(10, 2) DEFAULT 0 CHECK (network_costs_usd >= 0),
    top_services JSONB,
    recommendations JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_report_per_tenant_date UNIQUE(tenant_id, report_date)
);

-- Indexes for report queries
CREATE INDEX IF NOT EXISTS idx_cost_reports_tenant_date ON cost_reports_daily(tenant_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_cost_reports_date ON cost_reports_daily(report_date DESC);

-- Comment on table
COMMENT ON TABLE cost_reports_daily IS 'Pre-aggregated daily cost summaries';
COMMENT ON COLUMN cost_reports_daily.top_services IS 'Top 5 services by cost with breakdown';
COMMENT ON COLUMN cost_reports_daily.recommendations IS 'Automated cost optimization recommendations';

-- ============================================
-- 6. Views
-- ============================================

-- Current month spending view
CREATE OR REPLACE VIEW current_month_spending AS
SELECT
    ct.tenant_id,
    DATE_TRUNC('month', ct.date) as month,
    SUM(ct.estimated_cost_usd) as total_estimated_cost,
    SUM(CASE WHEN ct.service_category = 'ml' THEN ct.estimated_cost_usd ELSE 0 END) as ml_costs,
    SUM(CASE WHEN ct.service_category = 'api' THEN ct.estimated_cost_usd ELSE 0 END) as api_costs,
    SUM(CASE WHEN ct.service_category = 'compute' THEN ct.estimated_cost_usd ELSE 0 END) as compute_costs,
    SUM(CASE WHEN ct.service_category = 'storage' THEN ct.estimated_cost_usd ELSE 0 END) as storage_costs,
    SUM(CASE WHEN ct.service_category = 'network' THEN ct.estimated_cost_usd ELSE 0 END) as network_costs,
    COUNT(DISTINCT ct.service_name) as active_services,
    MAX(ct.date) as last_update_date
FROM cost_tracking ct
WHERE ct.date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY ct.tenant_id, DATE_TRUNC('month', ct.date);

COMMENT ON VIEW current_month_spending IS 'Current month cost summary by category';

-- Active budget with current spending
CREATE OR REPLACE VIEW budget_status AS
SELECT
    bc.tenant_id,
    bc.tier_name,
    bc.monthly_budget_usd,
    bc.config_json,
    bc.effective_from,
    cms.total_estimated_cost as current_month_spend,
    ROUND((cms.total_estimated_cost / bc.monthly_budget_usd * 100)::numeric, 2) as budget_used_percent,
    bc.monthly_budget_usd - cms.total_estimated_cost as remaining_budget,
    EXTRACT(DAY FROM CURRENT_DATE - DATE_TRUNC('month', CURRENT_DATE)::date) + 1 as days_elapsed,
    EXTRACT(DAY FROM (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::date) as days_in_month,
    cms.ml_costs,
    cms.compute_costs,
    cms.active_services
FROM budget_configs bc
LEFT JOIN current_month_spending cms ON bc.tenant_id = cms.tenant_id
WHERE bc.is_active = TRUE;

COMMENT ON VIEW budget_status IS 'Real-time budget status with current month spending';

-- Service cost ranking
CREATE OR REPLACE VIEW service_cost_ranking AS
SELECT
    ct.tenant_id,
    ct.service_name,
    ct.service_category,
    SUM(ct.estimated_cost_usd) as total_cost,
    AVG(ct.estimated_cost_usd) as avg_daily_cost,
    SUM(ct.usage_count) as total_usage,
    COUNT(*) as days_active,
    RANK() OVER (PARTITION BY ct.tenant_id ORDER BY SUM(ct.estimated_cost_usd) DESC) as cost_rank
FROM cost_tracking ct
WHERE ct.date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY ct.tenant_id, ct.service_name, ct.service_category;

COMMENT ON VIEW service_cost_ranking IS 'Service cost ranking for current month';

-- ============================================
-- 7. Triggers
-- ============================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to tables
CREATE TRIGGER update_budget_configs_updated_at
    BEFORE UPDATE ON budget_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cost_tracking_updated_at
    BEFORE UPDATE ON cost_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_quotas_updated_at
    BEFORE UPDATE ON service_quotas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cost_reports_daily_updated_at
    BEFORE UPDATE ON cost_reports_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-calculate next reset timestamp for quotas
CREATE OR REPLACE FUNCTION calculate_next_reset()
RETURNS TRIGGER AS $$
BEGIN
    NEW.next_reset = CASE NEW.reset_period
        WHEN 'hourly' THEN NEW.last_reset + INTERVAL '1 hour'
        WHEN 'daily' THEN NEW.last_reset + INTERVAL '1 day'
        WHEN 'monthly' THEN NEW.last_reset + INTERVAL '1 month'
        ELSE NULL
    END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_quota_next_reset
    BEFORE INSERT OR UPDATE ON service_quotas
    FOR EACH ROW
    EXECUTE FUNCTION calculate_next_reset();

-- ============================================
-- 8. Default Budget Tiers (Templates)
-- ============================================

-- Insert default tenant and budget tiers
INSERT INTO budget_configs (tier_name, monthly_budget_usd, config_json, notes) VALUES
-- Tier 1: MINIMAL ($0-$10/month) - Gold only, no AI
('minimal', 10.00, '{
  "enable_goldapi_collector": true,
  "enable_finnhub_collector": true,
  "enable_turkish_scrapers": true,
  "enable_crypto_market": false,
  "enable_reddit_collector": false,
  "enable_rss_collector": false,
  "enable_binance_collector": false,
  "scheduler_goldapi_interval": 120,
  "scheduler_finnhub_interval": 600,
  "scheduler_turkish_interval": 600,
  "goldapi_symbols": ["XAU"],
  "goldapi_currencies": ["USD", "EUR", "TRY"],
  "sentiment_lite_mode": true,
  "gemini_daily_limit": 0,
  "enable_ml_predictions": false,
  "enable_technical_analysis": true,
  "enable_alerts": true,
  "data_retention_bronze_days": 90,
  "data_retention_silver_days": 180
}', 'Gold-only tracking with rule-based sentiment (NO AI cost)'),

-- Tier 2: BASIC ($10-$50/month) - Gold with AI
('basic', 50.00, '{
  "enable_goldapi_collector": true,
  "enable_finnhub_collector": true,
  "enable_turkish_scrapers": true,
  "enable_rss_collector": true,
  "enable_crypto_market": false,
  "scheduler_goldapi_interval": 60,
  "scheduler_finnhub_interval": 300,
  "scheduler_rss_interval": 600,
  "goldapi_symbols": ["XAU", "XAG"],
  "goldapi_currencies": ["USD", "EUR", "TRY"],
  "sentiment_lite_mode": false,
  "gemini_daily_limit": 100,
  "gemini_model": "gemini-1.5-flash-001",
  "enable_ml_predictions": true,
  "enable_technical_analysis": true,
  "enable_gold_predictions": true,
  "enable_alerts": true,
  "data_retention_bronze_days": 180,
  "data_retention_silver_days": 365
}', 'Gold analysis with AI sentiment (100 req/day limit)'),

-- Tier 3: STANDARD ($50-$100/month) - Gold + Crypto
('standard', 100.00, '{
  "enable_crypto_market": true,
  "enable_gold_market": true,
  "enable_all_major_collectors": true,
  "scheduler_goldapi_interval": 60,
  "scheduler_finnhub_interval": 300,
  "scheduler_binance_interval": 60,
  "scheduler_reddit_interval": 600,
  "goldapi_symbols": ["XAU", "XAG", "XPT", "XPD"],
  "crypto_symbols": ["BTC", "ETH"],
  "sentiment_lite_mode": false,
  "gemini_daily_limit": 300,
  "enable_ml_predictions": true,
  "enable_analytics_dashboard": true,
  "data_retention_bronze_days": 365,
  "data_retention_silver_days": 730
}', 'Multi-market analysis with increased AI quota'),

-- Tier 4: PREMIUM ($100-$200/month) - Full platform
('premium', 200.00, '{
  "enable_crypto_market": true,
  "enable_gold_market": true,
  "enable_all_collectors": true,
  "scheduler_intervals_minimum": true,
  "gemini_daily_limit": 500,
  "enable_ml_predictions": true,
  "enable_advanced_ml": true,
  "enable_analytics_dashboard": true,
  "enable_backtesting": true,
  "data_retention_unlimited": true
}', 'Full platform with all features enabled')
ON CONFLICT DO NOTHING;

-- ============================================
-- 9. Sample Service Quotas
-- ============================================

-- Sample quotas for default tenant
INSERT INTO service_quotas (service_name, quota_type, quota_limit, reset_period) VALUES
('vertex-ai-gemini', 'daily_requests', 500, 'daily'),
('goldapi', 'monthly_requests', 50000, 'monthly'),
('finnhub', 'daily_requests', 60, 'daily'),
('bigquery', 'monthly_requests', 1000, 'monthly')
ON CONFLICT DO NOTHING;

-- ============================================
-- End of Budget Management Schema
-- ============================================
