"""Prometheus metrics for monitoring.

This module provides Prometheus metrics for the Sentilyze platform,
supporting both crypto and gold markets.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
from typing import Callable, Any
import time

# =============================================================================
# API Gateway Metrics
# =============================================================================

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# Rate limiting metrics
RATE_LIMIT_HITS = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['endpoint', 'user_id']
)

RATE_LIMIT_FAILURES = Counter(
    'rate_limit_failures_total',
    'Total rate limit check failures'
)

# Authentication metrics
AUTH_FAILURES = Counter(
    'auth_failures_total',
    'Total authentication failures',
    ['reason']
)

AUTH_SUCCESSES = Counter(
    'auth_successes_total',
    'Total successful authentications'
)

# =============================================================================
# Data Collection Metrics
# =============================================================================

COLLECTION_EVENTS = Counter(
    'collection_events_total',
    'Total data collection events',
    ['source', 'market_type', 'status']
)

COLLECTION_LATENCY = Histogram(
    'collection_duration_seconds',
    'Data collection duration',
    ['source', 'market_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

COLLECTION_ERRORS = Counter(
    'collection_errors_total',
    'Total collection errors',
    ['source', 'market_type', 'error_type']
)

# Price metrics
CURRENT_PRICE = Gauge(
    'asset_current_price',
    'Current asset price',
    ['symbol', 'currency', 'market_type']
)

PRICE_CHANGE = Gauge(
    'asset_price_change_percent',
    'Asset price change percentage',
    ['symbol', 'currency', 'market_type']
)

# =============================================================================
# Sentiment Analysis Metrics
# =============================================================================

SENTIMENT_PROCESSED = Counter(
    'sentiment_processed_total',
    'Total sentiment analyses processed',
    ['status', 'market_type']
)

SENTIMENT_LATENCY = Histogram(
    'sentiment_analysis_duration_seconds',
    'Sentiment analysis duration',
    ['market_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

SENTIMENT_SCORE = Gauge(
    'sentiment_score',
    'Current sentiment score',
    ['symbol', 'market_type']
)

SENTIMENT_CONFIDENCE = Gauge(
    'sentiment_confidence',
    'Sentiment confidence level',
    ['symbol', 'market_type']
)

# =============================================================================
# Market Context Metrics
# =============================================================================

REGIME_DETECTIONS = Counter(
    'regime_detections_total',
    'Total regime detections',
    ['regime_type', 'market_type']
)

ANOMALIES_DETECTED = Counter(
    'anomalies_detected_total',
    'Total anomalies detected',
    ['anomaly_type', 'severity', 'market_type']
)

CORRELATION_CALCULATIONS = Counter(
    'correlation_calculations_total',
    'Total correlation calculations',
    ['primary_symbol', 'secondary_symbol']
)

CURRENT_REGIME = Gauge(
    'current_market_regime',
    'Current market regime (0=neutral, 1=bull, -1=bear, 2=volatile)',
    ['symbol', 'market_type']
)

# =============================================================================
# System Metrics
# =============================================================================

CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result', 'backend']
)

CACHE_LATENCY = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation duration',
    ['operation', 'backend'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

BIGQUERY_OPERATIONS = Counter(
    'bigquery_operations_total',
    'Total BigQuery operations',
    ['operation', 'status']
)

BIGQUERY_LATENCY = Histogram(
    'bigquery_operation_duration_seconds',
    'BigQuery operation duration',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0]
)

PUBSUB_MESSAGES = Counter(
    'pubsub_messages_total',
    'Total Pub/Sub messages',
    ['operation', 'status', 'market_type']
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['service']
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker recorded failures',
    ['service']
)

# =============================================================================
# Service Info
# =============================================================================

SERVICE_INFO = Info(
    'sentilyze',
    'Sentilyze service information'
)

# =============================================================================
# Decorators
# =============================================================================

def track_request(endpoint: str):
    """Decorator to track HTTP request metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            method = "GET"
            
            try:
                response = await func(*args, **kwargs)
                status_code = getattr(response, 'status_code', 200)
                
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                
                REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(time.time() - start_time)
                
                return response
            except Exception as e:
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=500
                ).inc()
                raise
        
        return wrapper
    return decorator


def track_collection(source: str, market_type: str = "crypto"):
    """Decorator to track data collection metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                COLLECTION_EVENTS.labels(
                    source=source,
                    market_type=market_type,
                    status="success"
                ).inc()
                
                COLLECTION_LATENCY.labels(
                    source=source,
                    market_type=market_type
                ).observe(time.time() - start_time)
                
                return result
            except Exception as e:
                COLLECTION_EVENTS.labels(
                    source=source,
                    market_type=market_type,
                    status="error"
                ).inc()
                
                COLLECTION_ERRORS.labels(
                    source=source,
                    market_type=market_type,
                    error_type=type(e).__name__
                ).inc()
                
                raise
        
        return wrapper
    return decorator


def track_sentiment_analysis(market_type: str = "crypto"):
    """Decorator to track sentiment analysis metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                SENTIMENT_PROCESSED.labels(
                    status="success",
                    market_type=market_type
                ).inc()
                SENTIMENT_LATENCY.labels(market_type=market_type).observe(time.time() - start_time)
                
                # Record sentiment score if available
                if hasattr(result, 'sentiment') and hasattr(result.sentiment, 'score'):
                    symbol = kwargs.get('symbol', 'unknown')
                    SENTIMENT_SCORE.labels(symbol=symbol, market_type=market_type).set(result.sentiment.score)
                    SENTIMENT_CONFIDENCE.labels(symbol=symbol, market_type=market_type).set(result.sentiment.confidence)
                
                return result
            except Exception as e:
                SENTIMENT_PROCESSED.labels(
                    status="error",
                    market_type=market_type
                ).inc()
                raise
        
        return wrapper
    return decorator


def initialize_metrics(service_name: str, version: str = "4.0.0"):
    """Initialize service info metrics."""
    SERVICE_INFO.info({
        'service': service_name,
        'version': version,
        'platform': 'sentilyze-unified',
    })
