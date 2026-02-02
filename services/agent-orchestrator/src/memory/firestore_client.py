"""
Firestore Memory Client
Manages conversation history and context for agents
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from google.cloud import firestore

class FirestoreMemory:
    """Firestore client for agent memory management"""
    
    def __init__(self, project_id: str = None):
        self.db = firestore.Client(project=project_id)
        self.collection = 'agent_conversations'
        self.context_ttl_hours = 24  # Context expires after 24 hours
    
    def save_context(
        self,
        user_id: str,
        session_id: str,
        context: Dict[str, Any]
    ) -> bool:
        """Save conversation context to Firestore"""
        try:
            doc_id = f"{user_id}_{session_id}"
            doc_ref = self.db.collection(self.collection).document(doc_id)
            
            data = {
                'user_id': user_id,
                'session_id': session_id,
                'context': context,
                'timestamp': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=self.context_ttl_hours)
            }
            
            doc_ref.set(data)
            return True
            
        except Exception as e:
            print(f"Error saving context: {e}")
            return False
    
    def get_context(
        self,
        user_id: str,
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get conversation context from Firestore"""
        try:
            if not session_id:
                # Get most recent context for user
                docs = self.db.collection(self.collection)\
                    .where('user_id', '==', user_id)\
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                    .limit(1)\
                    .stream()
                
                for doc in docs:
                    data = doc.to_dict()
                    # Check if expired
                    if data.get('expires_at', datetime.now()) > datetime.now():
                        return data.get('context', {})
                    return {}
                
                return {}
            
            # Get specific session
            doc_id = f"{user_id}_{session_id}"
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Check if expired
                if data.get('expires_at', datetime.now()) > datetime.now():
                    return data.get('context', {})
            
            return {}
            
        except Exception as e:
            print(f"Error getting context: {e}")
            return {}
    
    def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> list:
        """Get conversation history"""
        try:
            docs = self.db.collection(self.collection)\
                .where('user_id', '==', user_id)\
                .where('session_id', '==', session_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            history = []
            for doc in docs:
                data = doc.to_dict()
                history.append({
                    'timestamp': data.get('timestamp'),
                    'context': data.get('context', {})
                })
            
            return history
            
        except Exception as e:
            print(f"Error getting history: {e}")
            return []
    
    def cleanup_expired(self) -> int:
        """Clean up expired context entries"""
        try:
            docs = self.db.collection(self.collection)\
                .where('expires_at', '<', datetime.now())\
                .stream()
            
            count = 0
            for doc in docs:
                doc.reference.delete()
                count += 1
            
            return count
            
        except Exception as e:
            print(f"Error cleaning up: {e}")
            return 0
