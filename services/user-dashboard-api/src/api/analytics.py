"""Analytics endpoints."""
from fastapi import APIRouter, Query
from google.cloud import bigquery

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/sentiment/overview")
async def sentiment_overview(symbol: str = Query("XAU")):
    """Get sentiment overview for symbol."""
    client = bigquery.Client()
    query = f"""
    SELECT
        DATE(processed_at) as date,
        AVG(sentiment_score) as avg_score,
        COUNT(*) as total_items
    FROM `sentilyze_dataset.sentiment_results`
    WHERE symbol = @symbol
    AND processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    GROUP BY date
    ORDER BY date DESC
    """
    job = client.query(query, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("symbol", "STRING", symbol)]
    ))
    return [dict(row) for row in job.result()]

@router.get("/predictions/recent")
async def recent_predictions(symbol: str = Query("XAU"), limit: int = 10):
    """Get recent predictions."""
    client = bigquery.Client()
    query = f"""
    SELECT *
    FROM `sentilyze_dataset.predictions`
    WHERE symbol = @symbol
    ORDER BY prediction_timestamp DESC
    LIMIT @limit
    """
    job = client.query(query, job_config=bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("symbol", "STRING", symbol),
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        ]
    ))
    return [dict(row) for row in job.result()]

@router.get("/market/trending")
async def trending_symbols():
    """Get trending symbols."""
    client = bigquery.Client()
    query = """
    SELECT symbol, COUNT(*) as mentions
    FROM `sentilyze_dataset.sentiment_results`
    WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY symbol
    ORDER BY mentions DESC
    LIMIT 10
    """
    job = client.query(query)
    return [dict(row) for row in job.result()]
