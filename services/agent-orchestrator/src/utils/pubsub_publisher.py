"""
Pub/Sub Publisher Client
Publishes events to Pub/Sub topics
"""

import json
from typing import Dict, Any
from google.cloud import pubsub_v1
from datetime import datetime

class PubSubPublisher:
    """Client for publishing events to Pub/Sub"""
    
    def __init__(self, project_id: str = None):
        self.publisher = pubsub_v1.PublisherClient()
        self.project_id = project_id
    
    def _get_topic_path(self, topic_name: str) -> str:
        """Get full topic path"""
        return self.publisher.topic_path(self.project_id, topic_name)
    
    def publish_risk_alert(self, alert_data: Dict[str, Any]) -> str:
        """Publish risk alert to Pub/Sub"""
        topic_path = self._get_topic_path('risk-alerts')
        
        message = {
            'type': 'risk_alert',
            'timestamp': datetime.now().isoformat(),
            'data': alert_data
        }
        
        data = json.dumps(message).encode('utf-8')
        future = self.publisher.publish(topic_path, data)
        return future.result()
    
    def publish_price_alert(self, alert_data: Dict[str, Any]) -> str:
        """Publish price alert to Pub/Sub"""
        topic_path = self._get_topic_path('price-alerts')
        
        message = {
            'type': 'price_alert',
            'timestamp': datetime.now().isoformat(),
            'data': alert_data
        }
        
        data = json.dumps(message).encode('utf-8')
        future = self.publisher.publish(topic_path, data)
        return future.result()
    
    def publish_audit_log(self, log_data: Dict[str, Any]) -> str:
        """Publish audit log to Pub/Sub"""
        topic_path = self._get_topic_path('audit-logs')
        
        message = {
            'type': 'audit',
            'timestamp': datetime.now().isoformat(),
            'data': log_data
        }
        
        data = json.dumps(message).encode('utf-8')
        future = self.publisher.publish(topic_path, data)
        return future.result()
    
    def publish_agent_command(self, command: str, payload: Dict[str, Any]) -> str:
        """Publish agent command to Pub/Sub"""
        topic_path = self._get_topic_path('agent-commands')
        
        message = {
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'payload': payload
        }
        
        data = json.dumps(message).encode('utf-8')
        future = self.publisher.publish(topic_path, data)
        return future.result()
