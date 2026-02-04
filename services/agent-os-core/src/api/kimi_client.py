"""Moonshot Kimi 2.5 API Client."""

import json
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = structlog.get_logger(__name__)


class KimiClient:
    """Client for Moonshot Kimi 2.5 API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        """Initialize Kimi client.

        Args:
            api_key: Moonshot API key (defaults to settings)
            base_url: API base URL (defaults to settings)
            model: Model name (defaults to settings)
            max_tokens: Maximum tokens for generation (defaults to settings)
            temperature: Sampling temperature (defaults to settings)
        """
        self.api_key = api_key or settings.MOONSHOT_API_KEY
        self.base_url = base_url or settings.MOONSHOT_BASE_URL
        self.model = model or settings.MOONSHOT_MODEL
        self.max_tokens = max_tokens or settings.MOONSHOT_MAX_TOKENS
        self.temperature = temperature or settings.MOONSHOT_TEMPERATURE

        if not self.api_key:
            raise ValueError("MOONSHOT_API_KEY is required")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "kimi_client.initialized",
            base_url=self.base_url,
            model=self.model,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate text using Kimi 2.5.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Response format specification

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.debug(
                "kimi_client.request",
                prompt_length=len(prompt),
                has_system_prompt=bool(system_prompt),
            )

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]

            logger.info(
                "kimi_client.response",
                prompt_length=len(prompt),
                response_length=len(content),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )

            return content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Multi-turn conversation using chat/completions.

        Sends a full conversation history to the LLM for contextual responses.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: System prompt (prepended automatically)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Assistant response text
        """
        full_messages = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.debug(
                "kimi_client.chat_request",
                message_count=len(messages),
                has_system_prompt=bool(system_prompt),
            )

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]

            logger.info(
                "kimi_client.chat_response",
                message_count=len(messages),
                response_length=len(content),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )

            return content

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate JSON response using Kimi 2.5.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature

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
            response_format={"type": "json_object"},
        )

        # Clean up any potential markdown
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)

    async def analyze_trends(
        self,
        content: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze content for trends using SCOUT methodology.

        Args:
            content: Content to analyze
            context: Additional context

        Returns:
            Trend analysis result
        """
        system_prompt = """You are SCOUT, a trend intelligence analyst inspired by Neil Patel and Gary Vaynerchuk.

Analyze the provided content and identify potential trends. Rate on:
- Viral Score (1-10): Likelihood of going viral
- Migration Probability (High/Med/Low): Cross-platform potential
- Format: Visual format type (ASMR, POV, Split-screen, etc.)

Respond in JSON format with these fields:
{
    "viral_score": float,
    "migration_probability": "High|Med|Low",
    "suggested_hook": "string",
    "format_type": "string",
    "target_platforms": ["string"],
    "keywords": ["string"]
}"""

        prompt = f"Content to analyze:\n{content}"
        if context:
            prompt += f"\n\nContext:\n{context}"

        return await self.generate_json(prompt, system_prompt)

    async def generate_content_idea(
        self,
        trend_data: Dict[str, Any],
        agent_role: str,
        target_audience: str,
    ) -> Dict[str, Any]:
        """Generate content idea based on trend data.

        Args:
            trend_data: Trend analysis data
            agent_role: Role of the agent (SETH, ECE, etc.)
            target_audience: Target audience description

        Returns:
            Content idea
        """
        system_prompt = f"""You are {agent_role}, a content strategist.

Based on the trend data provided, generate a content idea that:
1. Leverages the trend effectively
2. Matches the target audience
3. Has high engagement potential

Respond in JSON format with these fields:
{{
    "title": "string",
    "hook": "string",
    "content_outline": ["string"],
    "call_to_action": "string",
    "estimated_engagement": "High|Med|Low",
    "platforms": ["string"]
}}"""

        prompt = f"""Trend Data:
{json.dumps(trend_data, indent=2)}

Target Audience: {target_audience}

Generate a content idea based on this trend."""

        return await self.generate_json(prompt, system_prompt)

    async def generate_experiment_idea(
        self,
        metric: str,
        current_value: float,
        target_value: float,
    ) -> Dict[str, Any]:
        """Generate growth experiment idea using ELON methodology.

        Args:
            metric: Metric to improve (MRR, conversion, etc.)
            current_value: Current metric value
            target_value: Target metric value

        Returns:
            Experiment idea with ICE scoring
        """
        system_prompt = """You are ELON, a growth experimentation architect inspired by Sean Ellis.

Generate a growth experiment idea using the ICE scoring framework:
- Impact (1-10): Potential impact on the metric
- Confidence (1-10): Confidence in success
- Ease (1-10): Ease of implementation

Respond in JSON format with these fields:
{
    "hypothesis": "string",
    "experiment_name": "string",
    "ice_scores": {
        "impact": int,
        "confidence": int,
        "ease": int,
        "total": int
    },
    "target_metric": "string",
    "expected_lift": "string",
    "implementation_steps": ["string"],
    "duration_days": int
}"""

        prompt = f"""Metric: {metric}
Current Value: {current_value}
Target Value: {target_value}

Generate a growth experiment to improve this metric."""

        return await self.generate_json(prompt, system_prompt)
