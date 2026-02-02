from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
import json

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, agent_type: str, name: str, description: str):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.capabilities = []
        self.system_prompt = ""
    
    @abstractmethod
    def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str],
        asset: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a user message and return response"""
        pass
    
    def get_name(self) -> str:
        return self.name
    
    def get_description(self) -> str:
        return self.description
    
    def get_capabilities(self) -> List[str]:
        return self.capabilities
    
    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def create_session_id(self) -> str:
        """Generate unique session ID"""
        return f"{self.agent_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
