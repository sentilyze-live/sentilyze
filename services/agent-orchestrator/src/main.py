import os
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import functions_framework
from flask import Request, Response

# Import our modules
from agents.insight_agent import InsightNavigatorAgent
from agents.risk_agent import RiskGuardianAgent
from agents.interpreter_agent import DataInterpreterAgent
from agents.watchlist_agent import WatchlistManagerAgent
from agents.concierge_agent import OnboardingConciergeAgent
from utils.compliance_checker import ComplianceChecker
from utils.bigquery_client import BigQueryClient
from memory.firestore_client import FirestoreMemory
from utils.pubsub_publisher import PubSubPublisher

# Initialize clients
compliance_checker = ComplianceChecker()
firestore_memory = FirestoreMemory()
pubsub_publisher = PubSubPublisher()
bigquery_client = BigQueryClient()

# Agent registry
AGENTS = {
    'insight': InsightNavigatorAgent(),
    'risk': RiskGuardianAgent(),
    'interpreter': DataInterpreterAgent(),
    'watchlist': WatchlistManagerAgent(),
    'concierge': OnboardingConciergeAgent(),
}

@functions_framework.http
def handle_request(request: Request) -> Response:
    """
    Main HTTP entry point for agent orchestrator
    Handles chat requests, health checks, and monitoring tasks
    """
    
    # Set CORS headers
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        path = request.path
        
        # Route based on path
        if path == '/chat':
            return handle_chat(request, headers)
        elif path == '/health':
            return handle_health(headers)
        elif path == '/monitor-volatility':
            return handle_volatility_monitor(headers)
        elif path == '/check-price-alerts':
            return handle_price_alerts(headers)
        elif path.startswith('/agents/'):
            agent_type = path.split('/')[-1]
            return handle_agent_info(agent_type, headers)
        else:
            return json_response({
                'error': 'Not found',
                'available_endpoints': [
                    '/chat',
                    '/health',
                    '/agents/{type}',
                    '/monitor-volatility',
                    '/check-price-alerts'
                ]
            }, 404, headers)
            
    except Exception as e:
        print(f"Error in handle_request: {str(e)}")
        return json_response({
            'error': 'Internal server error',
            'message': str(e)
        }, 500, headers)


def handle_chat(request: Request, headers: Dict[str, str]) -> Response:
    """Handle chat messages with AI agents"""
    
    request_data = request.get_json(silent=True)
    if not request_data:
        return json_response({
            'error': 'Invalid JSON body'
        }, 400, headers)
    
    # Extract required fields
    user_id = request_data.get('user_id')
    message = request_data.get('message')
    agent_type = request_data.get('agent_type', 'insight')
    session_id = request_data.get('session_id')
    asset = request_data.get('asset')  # Optional: BTC, ETH, XAU, etc.
    
    if not user_id or not message:
        return json_response({
            'error': 'Missing required fields: user_id, message'
        }, 400, headers)
    
    # Detect language from message
    lang = 'tr' if any(ord(c) > 127 for c in message[:50]) else 'en'
    
    # Check compliance
    is_safe, reason = compliance_checker.check_input(message)
    if not is_safe:
        # Log the compliance violation
        log_conversation(
            user_id=user_id,
            agent_type=agent_type,
            session_id=session_id or 'unknown',
            user_message=message,
            ai_response="",
            compliance_check=f"BLOCKED: {reason}",
            sentiment_queried=[]
        )
        
        # Bilingual compliance response
        if lang == 'tr':
            blocked_response = "⚠️ Bu platform yatırım tavsiyesi vermemektedir. Sentilyze sosyal medya metinlerini analiz eden bir piyasa araştırma aracıdır."
            disclaimer = "Yatırım tavsiyesi değildir. Kripto varlıklar yüksek risk içerir."
        else:
            blocked_response = "⚠️ This platform does not provide investment advice. Sentilyze is a market research tool that analyzes social media texts."
            disclaimer = "Not investment advice. Crypto assets carry high risk."
        
        return json_response({
            'response': blocked_response,
            'agent_type': agent_type,
            'compliance': 'BLOCKED',
            'reason': reason,
            'language': lang,
            'disclaimer': disclaimer
        }, 200, headers)
    
    # Get the agent
    agent = AGENTS.get(agent_type)
    if not agent:
        return json_response({
            'error': f'Unknown agent type: {agent_type}',
            'available_agents': list(AGENTS.keys())
        }, 400, headers)
    
    # Process the message
    start_time = datetime.now()
    try:
        result = agent.process_message(
            user_id=user_id,
            message=message,
            session_id=session_id,
            asset=asset,
            context=firestore_memory.get_context(user_id, session_id)
        )
        
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Check output compliance
        response = compliance_checker.check_output(result['response'])
        
        # Get language from agent result or detect from message
        response_lang = result.get('language', lang)
        
        # Add bilingual disclaimer if not present
        if '⚠️' not in response:
            if response_lang == 'tr':
                response += "\n\n⚠️ BU BİLGİLER YATIRIM TAVSİYESİ DEĞİLDİR. Kripto varlıklar yüksek risk içerir."
                disclaimer = "Yatırım tavsiyesi değildir. Kripto varlıklar yüksek risk içerir."
            else:
                response += "\n\n⚠️ THIS IS NOT INVESTMENT ADVICE. Crypto assets carry high risk."
                disclaimer = "Not investment advice. Crypto assets carry high risk."
        else:
            disclaimer = "Not investment advice. Crypto assets carry high risk." if response_lang == 'en' else "Yatırım tavsiyesi değildir. Kripto varlıklar yüksek risk içerir."
        
        # Log the conversation
        log_conversation(
            user_id=user_id,
            agent_type=agent_type,
            session_id=session_id or result.get('session_id', 'unknown'),
            user_message=message,
            ai_response=response,
            compliance_check='PASSED',
            sentiment_queried=result.get('sentiment_queried', []),
            response_time_ms=response_time_ms
        )
        
        # Save context for next message
        firestore_memory.save_context(
            user_id=user_id,
            session_id=session_id or result.get('session_id'),
            context={
                'last_agent': agent_type,
                'last_asset': asset,
                'last_message': message,
                'last_response': response,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        return json_response({
            'response': response,
            'agent_type': agent_type,
            'session_id': result.get('session_id', session_id),
            'compliance': 'PASSED',
            'language': response_lang,
            'response_time_ms': response_time_ms,
            'sentiment_data': result.get('sentiment_data'),
            'disclaimer': disclaimer
        }, 200, headers)
        
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return json_response({
            'error': 'Error processing message',
            'message': str(e)
        }, 500, headers)


def handle_health(headers: Dict[str, str]) -> Response:
    """Health check endpoint"""
    return json_response({
        'status': 'healthy',
        'service': 'agent-orchestrator',
        'timestamp': datetime.now().isoformat(),
        'agents': list(AGENTS.keys()),
        'version': '1.0.0'
    }, 200, headers)


def handle_volatility_monitor(headers: Dict[str, str]) -> Response:
    """Monitor market volatility and trigger risk alerts"""
    try:
        # Get the risk agent
        risk_agent = AGENTS['risk']
        
        # Check volatility
        alerts = risk_agent.check_volatility()
        
        # Publish alerts if any
        for alert in alerts:
            pubsub_publisher.publish_risk_alert(alert)
        
        return json_response({
            'status': 'success',
            'alerts_triggered': len(alerts),
            'timestamp': datetime.now().isoformat()
        }, 200, headers)
        
    except Exception as e:
        print(f"Error in volatility monitor: {str(e)}")
        return json_response({
            'error': str(e)
        }, 500, headers)


def handle_price_alerts(headers: Dict[str, str]) -> Response:
    """Check price alerts for users"""
    try:
        # Get the watchlist manager agent
        watchlist_agent = AGENTS['watchlist']
        
        # Check price alerts
        alerts = watchlist_agent.check_price_alerts()
        
        # Publish alerts if any
        for alert in alerts:
            pubsub_publisher.publish_price_alert(alert)
        
        return json_response({
            'status': 'success',
            'alerts_triggered': len(alerts),
            'timestamp': datetime.now().isoformat()
        }, 200, headers)
        
    except Exception as e:
        print(f"Error in price alerts: {str(e)}")
        return json_response({
            'error': str(e)
        }, 500, headers)


def handle_agent_info(agent_type: str, headers: Dict[str, str]) -> Response:
    """Get information about a specific agent"""
    agent = AGENTS.get(agent_type)
    if not agent:
        return json_response({
            'error': f'Unknown agent type: {agent_type}',
            'available_agents': list(AGENTS.keys())
        }, 404, headers)
    
    # Bilingual agent info
    agent_names = {
        'insight': {'tr': 'Insight Navigator', 'en': 'Insight Navigator'},
        'risk': {'tr': 'Risk Guardian', 'en': 'Risk Guardian'},
        'interpreter': {'tr': 'Data Interpreter', 'en': 'Data Interpreter'},
        'watchlist': {'tr': 'Watchlist Manager', 'en': 'Watchlist Manager'},
        'concierge': {'tr': 'Platform Guide', 'en': 'Platform Guide'}
    }
    
    agent_descriptions = {
        'insight': {
            'tr': 'Piyasa duyarlılığı (sentiment) ve trend analizi aracı',
            'en': 'Market sentiment and trend analysis tool'
        },
        'risk': {
            'tr': 'Risk eğitimi ve finansal okuryazarlık',
            'en': 'Risk education and financial literacy'
        },
        'interpreter': {
            'tr': 'Teknik göstergeler ve veri açıklamaları',
            'en': 'Technical indicators and data explanations'
        },
        'watchlist': {
            'tr': 'İzleme listesi ve fiyat alarm takibi',
            'en': 'Watchlist and price alert tracking'
        },
        'concierge': {
            'tr': 'Platform rehberi ve kullanım yardımı',
            'en': 'Platform guide and usage help'
        }
    }
    
    return json_response({
        'agent_type': agent_type,
        'name': agent_names.get(agent_type, {}).get('en', agent.get_name()),
        'name_tr': agent_names.get(agent_type, {}).get('tr', agent.get_name()),
        'description': agent_descriptions.get(agent_type, {}).get('en', agent.get_description()),
        'description_tr': agent_descriptions.get(agent_type, {}).get('tr', agent.get_description()),
        'capabilities': agent.get_capabilities(),
        'disclaimer_en': 'Not investment advice. For educational purposes only.',
        'disclaimer_tr': 'Yatırım tavsiyesi değildir. Sadece eğitim amaçlıdır.'
    }, 200, headers)


def log_conversation(
    user_id: str,
    agent_type: str,
    session_id: str,
    user_message: str,
    ai_response: str,
    compliance_check: str,
    sentiment_queried: List[str],
    response_time_ms: int = 0,
    ip_address: str = None
):
    """Log conversation to BigQuery for audit"""
    try:
        bigquery_client.insert_conversation({
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'agent_type': agent_type,
            'session_id': session_id,
            'user_message': user_message[:1000],  # Truncate if too long
            'ai_response': ai_response[:2000],     # Truncate if too long
            'compliance_check': compliance_check,
            'sentiment_queried': sentiment_queried,
            'response_time_ms': response_time_ms,
            'ip_address': ip_address
        })
    except Exception as e:
        print(f"Error logging conversation: {str(e)}")


def json_response(data: Dict[str, Any], status_code: int = 200, headers: Dict[str, str] = None) -> Response:
    """Helper to create JSON response"""
    if headers is None:
        headers = {}
    
    headers['Content-Type'] = 'application/json'
    
    return Response(
        response=json.dumps(data, ensure_ascii=False),
        status=status_code,
        headers=headers
    )
