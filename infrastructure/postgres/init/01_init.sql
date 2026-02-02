-- Sentilyze PostgreSQL Database Initialization
-- Creates tables for prediction tracking and validation

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Predictions table - tracks all generated predictions
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_context_id UUID,
    market_type VARCHAR(20) NOT NULL CHECK (market_type IN ('crypto', 'gold')),
    asset_symbol VARCHAR(10) NOT NULL,
    prediction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    prediction_type VARCHAR(50) NOT NULL DEFAULT 'price_direction',
    prediction_horizon_hours INTEGER NOT NULL DEFAULT 24,
    current_price DECIMAL(18, 8) NOT NULL,
    predicted_price DECIMAL(18, 8),
    predicted_direction VARCHAR(10) NOT NULL CHECK (predicted_direction IN ('up', 'down', 'sideways')),
    predicted_change_percent DECIMAL(8, 4),
    confidence_score DECIMAL(4, 3) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    probability_up DECIMAL(4, 3) CHECK (probability_up >= 0 AND probability_up <= 1),
    probability_down DECIMAL(4, 3) CHECK (probability_down >= 0 AND probability_down <= 1),
    probability_sideways DECIMAL(4, 3) CHECK (probability_sideways >= 0 AND probability_sideways <= 1),
    sentiment_score DECIMAL(4, 3),
    technical_indicators JSONB,
    model_version VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    feature_importance JSONB,
    validated BOOLEAN DEFAULT FALSE,
    validation_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Prediction validation results table
CREATE TABLE IF NOT EXISTS prediction_validations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    validation_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    actual_price DECIMAL(18, 8),
    actual_direction VARCHAR(10) CHECK (actual_direction IN ('up', 'down', 'sideways')),
    actual_change_percent DECIMAL(8, 4),
    prediction_error DECIMAL(8, 4),
    direction_correct BOOLEAN NOT NULL,
    within_confidence_interval BOOLEAN,
    accuracy_score DECIMAL(4, 3) CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Alert history table
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID REFERENCES predictions(id) ON DELETE SET NULL,
    market_type VARCHAR(20) NOT NULL,
    asset_symbol VARCHAR(10) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    trigger_value DECIMAL(18, 8),
    threshold_value DECIMAL(18, 8),
    channels TEXT[] DEFAULT '{}',
    recipients TEXT[] DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'acknowledged')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    market_type VARCHAR(20),
    asset_symbol VARCHAR(10),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_predictions INTEGER NOT NULL DEFAULT 0,
    correct_predictions INTEGER NOT NULL DEFAULT 0,
    accuracy_pct DECIMAL(5, 2),
    avg_confidence DECIMAL(4, 3),
    avg_mae DECIMAL(18, 8),
    avg_rmse DECIMAL(18, 8),
    sharpe_ratio DECIMAL(8, 4),
    max_drawdown_pct DECIMAL(8, 4),
    features_used TEXT[],
    training_samples INTEGER,
    validation_samples INTEGER,
    training_duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_predictions_market_asset 
    ON predictions(market_type, asset_symbol);

CREATE INDEX IF NOT EXISTS idx_predictions_timestamp 
    ON predictions(prediction_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_validated 
    ON predictions(validated, validation_timestamp) 
    WHERE validated = FALSE;

CREATE INDEX IF NOT EXISTS idx_predictions_model 
    ON predictions(model_version, model_name);

CREATE INDEX IF NOT EXISTS idx_validations_prediction 
    ON prediction_validations(prediction_id);

CREATE INDEX IF NOT EXISTS idx_validations_direction_correct 
    ON prediction_validations(direction_correct, accuracy_score);

CREATE INDEX IF NOT EXISTS idx_alerts_market_asset 
    ON alert_history(market_type, asset_symbol);

CREATE INDEX IF NOT EXISTS idx_alerts_created 
    ON alert_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_status 
    ON alert_history(status) 
    WHERE status IN ('pending', 'failed');

CREATE INDEX IF NOT EXISTS idx_model_performance_version 
    ON model_performance(model_version, start_date DESC);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for predictions table
DROP TRIGGER IF EXISTS update_predictions_updated_at ON predictions;
CREATE TRIGGER update_predictions_updated_at
    BEFORE UPDATE ON predictions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for prediction accuracy summary
CREATE OR REPLACE VIEW prediction_accuracy_summary AS
SELECT 
    p.market_type,
    p.asset_symbol,
    p.model_version,
    DATE(p.prediction_timestamp) as prediction_date,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN pv.direction_correct THEN 1 ELSE 0 END) as correct_directions,
    ROUND(SUM(CASE WHEN pv.direction_correct THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as accuracy_pct,
    ROUND(AVG(pv.accuracy_score), 4) as avg_accuracy_score,
    ROUND(AVG(ABS(pv.prediction_error)), 4) as avg_mae,
    ROUND(AVG(p.confidence_score), 4) as avg_confidence
FROM predictions p
LEFT JOIN prediction_validations pv ON p.id = pv.prediction_id
WHERE p.validated = TRUE
GROUP BY p.market_type, p.asset_symbol, p.model_version, DATE(p.prediction_timestamp)
ORDER BY prediction_date DESC;

-- Create view for pending validations
CREATE OR REPLACE VIEW pending_validations AS
SELECT 
    p.id,
    p.market_type,
    p.asset_symbol,
    p.prediction_timestamp,
    p.prediction_horizon_hours,
    p.predicted_direction,
    p.predicted_change_percent,
    p.confidence_score,
    p.model_version,
    CASE 
        WHEN CURRENT_TIMESTAMP >= p.prediction_timestamp + INTERVAL '1 hour' * p.prediction_horizon_hours 
        THEN TRUE 
        ELSE FALSE 
    END as is_ready_for_validation
FROM predictions p
WHERE p.validated = FALSE
ORDER BY p.prediction_timestamp;

-- Insert sample data for testing (remove in production)
-- INSERT INTO predictions (market_type, asset_symbol, prediction_timestamp, prediction_type, prediction_horizon_hours, 
--     current_price, predicted_direction, predicted_change_percent, confidence_score, model_version, model_name)
-- VALUES 
--     ('crypto', 'BTC', CURRENT_TIMESTAMP - INTERVAL '25 hours', 'price_direction', 24, 45000.00, 'up', 2.5, 0.75, 'v1.0.0', 'ensemble_lstm'),
--     ('crypto', 'ETH', CURRENT_TIMESTAMP - INTERVAL '25 hours', 'price_direction', 24, 3000.00, 'down', -1.8, 0.68, 'v1.0.0', 'ensemble_lstm'),
--     ('gold', 'XAU', CURRENT_TIMESTAMP - INTERVAL '25 hours', 'price_direction', 24, 2000.00, 'up', 0.5, 0.82, 'v1.0.0', 'ensemble_lstm');
