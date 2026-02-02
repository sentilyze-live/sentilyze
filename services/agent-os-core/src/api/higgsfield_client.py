"""Higgsfield AI Visual Generation API Client (Updated for new API)."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = structlog.get_logger(__name__)


class HiggsfieldClient:
    """Client for Higgsfield AI Visual Generation API (Async Queue-based)."""

    # Default model
    DEFAULT_MODEL = "higgsfield-ai/soul/standard"

    def __init__(
        self,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize Higgsfield client.

        Args:
            api_key_id: Higgsfield API Key ID
            api_key_secret: Higgsfield API Key Secret
            base_url: API base URL
        """
        self.api_key_id = api_key_id or settings.HIGGSFIELD_API_KEY_ID
        self.api_key_secret = api_key_secret or settings.HIGGSFIELD_API_KEY_SECRET
        self.base_url = base_url or "https://platform.higgsfield.ai"

        if not self.api_key_id or not self.api_key_secret:
            raise ValueError("HIGGSFIELD_API_KEY_ID and HIGGSFIELD_API_KEY_SECRET are required")

        # Auth header format: "Key {api_key_id}:{api_key_secret}"
        self.headers = {
            "Authorization": f"Key {self.api_key_id}:{self.api_key_secret}",
            "Content-Type": "application/json",
        }

        logger.info(
            "higgsfield_client.initialized",
            base_url=self.base_url,
            api_key_id=self.api_key_id[:8] + "...",  # Log only first 8 chars for security
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def submit_generation_request(
        self,
        prompt: str,
        model_id: str = None,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
    ) -> Dict[str, Any]:
        """Submit a generation request to the queue.

        Args:
            prompt: Image generation prompt
            model_id: Model identifier (defaults to soul/standard)
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1, etc.)
            resolution: Resolution (720p, 1080p, etc.)

        Returns:
            Request info including request_id and status_url
        """
        model = model_id or self.DEFAULT_MODEL
        endpoint = f"{self.base_url}/{model}"

        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug(
                "higgsfield_client.submit_request",
                prompt_length=len(prompt),
                model=model,
            )

            response = await client.post(
                endpoint,
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            logger.info(
                "higgsfield_client.request_submitted",
                request_id=data.get("request_id"),
                status=data.get("status"),
            )

            return data

    async def check_request_status(self, request_id: str) -> Dict[str, Any]:
        """Check the status of a generation request.

        Args:
            request_id: The request ID returned from submit_generation_request

        Returns:
            Status information including result URL if completed
        """
        endpoint = f"{self.base_url}/requests/{request_id}/status"

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug("higgsfield_client.check_status", request_id=request_id)

            response = await client.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            return data

    async def wait_for_completion(
        self,
        request_id: str,
        max_wait_seconds: int = 300,
        poll_interval: int = 5,
    ) -> Optional[str]:
        """Wait for a generation request to complete.

        Args:
            request_id: The request ID
            max_wait_seconds: Maximum time to wait
            poll_interval: Seconds between status checks

        Returns:
            Image URL if successful, None if failed or timeout
        """
        logger.info(
            "higgsfield_client.waiting",
            request_id=request_id,
            max_wait=max_wait_seconds,
        )

        start_time = asyncio.get_event_loop().time()

        while True:
            status_data = await self.check_request_status(request_id)
            status = status_data.get("status")

            if status == "completed":
                # Get the result URL from the status response
                # The API returns images in an array
                result_url = None
                
                # Try to get from images array first
                if "images" in status_data and len(status_data["images"]) > 0:
                    result_url = status_data["images"][0].get("url")
                # Fallback to other possible locations
                elif status_data.get("result_url"):
                    result_url = status_data.get("result_url")
                elif status_data.get("output", {}).get("url"):
                    result_url = status_data.get("output", {}).get("url")
                
                logger.info(
                    "higgsfield_client.completed",
                    request_id=request_id,
                    result_url=result_url,
                )
                return result_url

            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                logger.error(
                    "higgsfield_client.failed",
                    request_id=request_id,
                    error=error,
                )
                return None

            elif status in ["queued", "processing", "in_progress"]:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait_seconds:
                    logger.error(
                        "higgsfield_client.timeout",
                        request_id=request_id,
                        elapsed=elapsed,
                    )
                    return None

                logger.debug(
                    "higgsfield_client.pending",
                    request_id=request_id,
                    status=status,
                    elapsed=f"{elapsed:.1f}s",
                )
                await asyncio.sleep(poll_interval)

            else:
                logger.warning(
                    "higgsfield_client.unknown_status",
                    request_id=request_id,
                    status=status,
                )
                await asyncio.sleep(poll_interval)

    async def generate_image(
        self,
        prompt: str,
        model_id: str = None,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        max_wait_seconds: int = 300,
    ) -> Dict[str, Any]:
        """Generate an image (submit request and wait for completion).

        Args:
            prompt: Image generation prompt
            model_id: Model identifier
            aspect_ratio: Aspect ratio
            resolution: Resolution
            max_wait_seconds: Maximum time to wait for completion

        Returns:
            Generation result with image URL
        """
        # Submit request
        request_data = await self.submit_generation_request(
            prompt=prompt,
            model_id=model_id,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

        request_id = request_data.get("request_id")
        if not request_id:
            raise ValueError("No request_id in response")

        # Wait for completion
        image_url = await self.wait_for_completion(
            request_id=request_id,
            max_wait_seconds=max_wait_seconds,
        )

        if image_url:
            return {
                "success": True,
                "request_id": request_id,
                "image_url": image_url,
                "prompt": prompt,
            }
        else:
            return {
                "success": False,
                "request_id": request_id,
                "error": "Generation failed or timed out",
            }

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request.

        Args:
            request_id: The request ID to cancel

        Returns:
            True if cancelled successfully
        """
        endpoint = f"{self.base_url}/requests/{request_id}/cancel"

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("higgsfield_client.cancel_request", request_id=request_id)

            try:
                response = await client.post(endpoint, headers=self.headers)
                response.raise_for_status()
                logger.info("higgsfield_client.cancelled", request_id=request_id)
                return True
            except Exception as e:
                logger.error("higgsfield_client.cancel_failed", request_id=request_id, error=str(e))
                return False
