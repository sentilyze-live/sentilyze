"""
BigQuery Client
Queries sentiment and market data for agents
"""

from typing import Dict, Any, List
from google.cloud import bigquery
from datetime import datetime, timedelta

class BigQueryClient:
    """BigQuery client for querying market and sentiment data"""
    
    def __init__(self, project_id: str = None, dataset: str = 'sentilyze_dataset'):
        self.client = bigquery.Client(project=project_id)
        self.dataset = dataset
    
    def get_latest_sentiment(self, asset: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get latest sentiment data for an asset"""
        query = f"""
        SELECT 
            timestamp,
            sentiment_score,
            sentiment_label,
            confidence,
            mention_count,
            market_type
        FROM `{self.client.project}.{self.dataset}.sentiment_analysis`
        WHERE asset_symbol = @asset
        AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("asset", "STRING", asset),
                bigquery.ScalarQueryParameter("hours", "INT64", hours)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            data = []
            for row in results:
                data.append({
                    'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                    'sentiment_score': row.sentiment_score,
                    'sentiment_label': row.sentiment_label,
                    'confidence': row.confidence,
                    'mention_count': row.mention_count,
                    'market_type': row.market_type
                })
            
            return data
            
        except Exception as e:
            print(f"Error querying sentiment: {e}")
            return []
    
    def get_predictions(self, asset: str, horizon_hours: int = 24) -> List[Dict[str, Any]]:
        """Get active predictions for an asset"""
        query = f"""
        SELECT 
            prediction_timestamp,
            predicted_direction,
            confidence_score,
            prediction_horizon_hours,
            model_version
        FROM `{self.client.project}.{self.dataset}.predictions`
        WHERE asset_symbol = @asset
        AND prediction_horizon_hours = @horizon
        AND prediction_timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ORDER BY prediction_timestamp DESC
        LIMIT 10
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("asset", "STRING", asset),
                bigquery.ScalarQueryParameter("horizon", "INT64", horizon_hours)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            data = []
            for row in results:
                data.append({
                    'timestamp': row.prediction_timestamp.isoformat() if row.prediction_timestamp else None,
                    'direction': row.predicted_direction,
                    'confidence': row.confidence_score,
                    'horizon': row.prediction_horizon_hours,
                    'model': row.model_version
                })
            
            return data
            
        except Exception as e:
            print(f"Error querying predictions: {e}")
            return []
    
    def get_market_context(self, asset: str) -> Dict[str, Any]:
        """Get latest market context (technical indicators)"""
        query = f"""
        SELECT 
            timestamp,
            rsi_14,
            macd,
            bollinger_upper,
            bollinger_lower,
            ma_20,
            volume
        FROM `{self.client.project}.{self.dataset}.market_context`
        WHERE asset_symbol = @asset
        ORDER BY timestamp DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("asset", "STRING", asset)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return {
                    'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                    'rsi': row.rsi_14,
                    'macd': row.macd,
                    'bollinger_upper': row.bollinger_upper,
                    'bollinger_lower': row.bollinger_lower,
                    'ma_20': row.ma_20,
                    'volume': row.volume
                }
            
            return {}
            
        except Exception as e:
            print(f"Error querying market context: {e}")
            return {}
    
    def insert_conversation(self, conversation_data: Dict[str, Any]) -> bool:
        """Insert conversation audit log"""
        query = f"""
        INSERT INTO `{self.client.project}.agent_audit_logs.conversations`
        (timestamp, user_id, agent_type, session_id, user_message, 
         ai_response, compliance_check, sentiment_queried, response_time_ms, ip_address)
        VALUES
        (@timestamp, @user_id, @agent_type, @session_id, @user_message,
         @ai_response, @compliance_check, @sentiment_queried, @response_time_ms, @ip_address)
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("timestamp", "TIMESTAMP", conversation_data.get('timestamp')),
                bigquery.ScalarQueryParameter("user_id", "STRING", conversation_data.get('user_id')),
                bigquery.ScalarQueryParameter("agent_type", "STRING", conversation_data.get('agent_type')),
                bigquery.ScalarQueryParameter("session_id", "STRING", conversation_data.get('session_id')),
                bigquery.ScalarQueryParameter("user_message", "STRING", conversation_data.get('user_message')),
                bigquery.ScalarQueryParameter("ai_response", "STRING", conversation_data.get('ai_response')),
                bigquery.ScalarQueryParameter("compliance_check", "STRING", conversation_data.get('compliance_check')),
                bigquery.ScalarQueryParameter("sentiment_queried", "STRING", conversation_data.get('sentiment_queried', [])),
                bigquery.ScalarQueryParameter("response_time_ms", "INTEGER", conversation_data.get('response_time_ms', 0)),
                bigquery.ScalarQueryParameter("ip_address", "STRING", conversation_data.get('ip_address'))
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()
            return True
            
        except Exception as e:
            print(f"Error inserting conversation: {e}")
            return False
