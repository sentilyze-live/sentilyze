"""Response transformation middleware for snake_case to camelCase conversion.

This middleware automatically transforms all JSON responses from snake_case
(Python convention) to camelCase (JavaScript convention) for frontend compatibility.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from typing import Callable

from ..utils.transformers import transform_dict_keys
from sentilyze_core import get_logger

logger = get_logger(__name__)


class ResponseTransformerMiddleware(BaseHTTPMiddleware):
    """Middleware to transform all JSON responses to camelCase.

    This middleware intercepts all JSON responses and transforms field names
    from snake_case to camelCase. It preserves the response status and headers.

    The transformation is applied recursively to nested objects and arrays.
    Non-JSON responses are passed through unchanged.

    Example:
        Input response:  {"change_percent": 2.5, "high_price": 2700}
        Output response: {"changePercent": 2.5, "highPrice": 2700}
    """

    def __init__(self, app: ASGIApp, enable_transformation: bool = True):
        """Initialize the middleware.

        Args:
            app: The ASGI application
            enable_transformation: Enable/disable transformation (default: True)
        """
        super().__init__(app)
        self.enable_transformation = enable_transformation

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and transform the response.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response with transformed JSON body (if applicable)
        """
        # Skip transformation if disabled
        if not self.enable_transformation:
            return await call_next(request)

        # Call the next middleware/endpoint
        response = await call_next(request)

        # Only transform JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Try to transform the body
        try:
            data = json.loads(body)

            # Transform to camelCase
            transformed = transform_dict_keys(data)
            new_body = json.dumps(transformed, ensure_ascii=False).encode()

            # Update headers with correct Content-Length
            headers = dict(response.headers)
            headers["content-length"] = str(len(new_body))

            # Create new response with transformed body
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # If transformation fails, log and return original
            logger.warning(
                "Failed to transform response body",
                error=str(e),
                path=request.url.path
            )
            headers = dict(response.headers)
            headers["content-length"] = str(len(body))
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(
                "Unexpected error in response transformation",
                error=str(e),
                path=request.url.path
            )
            headers = dict(response.headers)
            headers["content-length"] = str(len(body))
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
