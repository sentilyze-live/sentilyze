"""Vertex AI client for cost-effective AI operations."""

import json
from typing import Any, Dict, List, Optional

import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = structlog.get_logger(__name__)


class VertexAIClient:
    """Client for Google Vertex AI (Gemini models) - Cost-effective alternative to Kimi."""

    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """Initialize Vertex AI client.
        
        Args:
            project_id: GCP project ID
            location: Vertex AI location
        """
        self.project_id = project_id or settings.VERTEX_AI_PROJECT_ID
        self.location = location or settings.VERTEX_AI_LOCATION
        
        # Initialize Vertex AI
        if settings.ENABLE_VERTEX_AI_FOR_AGENTS:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                self._initialized = True
                logger.info("vertex_ai.initialized", project=self.project_id, location=self.location)
            except Exception as e:
                logger.error("vertex_ai.init_failed", error=str(e))
                self._initialized = False
        else:
            self._initialized = False
            logger.info("vertex_ai.disabled")
        
        # Initialize models
        self._models: Dict[str, GenerativeModel] = {}
    
    def _get_model(self, model_name: str) -> GenerativeModel:
        """Get or create model instance.
        
        Args:
            model_name: Model name (e.g., gemini-1.5-flash-001)
            
        Returns:
            GenerativeModel instance
        """
        if model_name not in self._models:
            self._models[model_name] = GenerativeModel(model_name)
        return self._models[model_name]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> str:
        """Generate text using Vertex AI.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum output tokens
            model: Model to use (defaults to flash for cost efficiency)
            
        Returns:
            Generated text
        """
        if not self._initialized:
            raise RuntimeError("Vertex AI not initialized")
        
        model_name = model or settings.VERTEX_AI_MODEL_GEMINI_FLASH
        generative_model = self._get_model(model_name)
        
        # Build prompt with system instructions
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Configure generation
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=0.95,
            top_k=40,
        )
        
        try:
            logger.debug(
                "vertex_ai.generate_request",
                model=model_name,
                prompt_length=len(full_prompt),
            )
            
            response = generative_model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )
            
            content = response.text
            
            logger.info(
                "vertex_ai.generate_success",
                model=model_name,
                prompt_length=len(full_prompt),
                response_length=len(content),
            )
            
            return content
            
        except Exception as e:
            logger.error("vertex_ai.generate_error", error=str(e), model=model_name)
            raise
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate JSON response using Vertex AI.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature
            model: Model to use
            
        Returns:
            Parsed JSON response
        """
        # Add JSON instruction to system prompt
        json_instruction = (
            "You must respond with valid JSON only. "
            "Do not include any markdown formatting, code blocks, or explanatory text. "
            "Only return the JSON object."
        )
        
        if system_prompt:
            full_system_prompt = f"{system_prompt}\n\n{json_instruction}"
        else:
            full_system_prompt = json_instruction
        
        content = await self.generate(
            prompt=prompt,
            system_prompt=full_system_prompt,
            temperature=temperature,
            model=model,
        )
        
        # Clean up potential markdown
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        return json.loads(content)
    
    async def generate_for_agent(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        require_json: bool = False,
    ) -> Any:
        """Generate response optimized for specific agent.
        
        Routes to appropriate model based on agent and configuration.
        
        Args:
            agent_name: Agent name (zara, elon, seth, etc.)
            prompt: User prompt
            system_prompt: System instructions
            require_json: Whether to return JSON
            
        Returns:
            Generated content (str or dict)
        """
        # Determine if we should use Vertex AI or Kimi based on agent
        use_vertex = False
        model = settings.VERTEX_AI_MODEL_GEMINI_FLASH
        
        if agent_name.upper() == "ZARA" and settings.USE_VERTEX_FOR_ZARA:
            use_vertex = True
            logger.debug("vertex_ai.route_zara", use_vertex=True)
        elif agent_name.upper() == "ELON" and settings.USE_VERTEX_FOR_ELON:
            use_vertex = True
            logger.debug("vertex_ai.route_elon", use_vertex=True)
        elif agent_name.upper() == "SETH" and settings.USE_VERTEX_FOR_SETH_METADATA:
            use_vertex = True
            model = settings.VERTEX_AI_MODEL_GEMINI_PRO  # Use pro for content
            logger.debug("vertex_ai.route_seth", use_vertex=True)
        
        if use_vertex and self._initialized:
            try:
                if require_json:
                    return await self.generate_json(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.7,
                        model=model,
                    )
                else:
                    return await self.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.7,
                        model=model,
                    )
            except Exception as e:
                logger.warning(
                    "vertex_ai.fallback_to_kimi",
                    agent=agent_name,
                    error=str(e),
                )
                # Fall back to Kimi if Vertex AI fails
                return None
        
        # Return None to indicate Vertex AI not used (caller should use Kimi)
        return None


# Global client instance
vertex_ai_client = VertexAIClient()
