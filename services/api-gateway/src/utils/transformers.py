"""Response transformation utilities for snake_case to camelCase conversion.

This module provides utilities to transform API responses from Python's
snake_case convention to JavaScript's camelCase convention for frontend compatibility.
"""

from typing import Any, Dict, List, Set
from datetime import datetime


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case string to camelCase.

    Args:
        snake_str: String in snake_case format

    Returns:
        String in camelCase format

    Examples:
        >>> to_camel_case("change_percent")
        'changePercent'
        >>> to_camel_case("high_price")
        'highPrice'
        >>> to_camel_case("sentiment_count")
        'sentimentCount'
    """
    components = snake_str.split('_')
    # First component stays lowercase, rest are title case
    return components[0] + ''.join(x.title() for x in components[1:])


def transform_dict_keys(data: Any, skip_keys: Set[str] = None) -> Any:
    """Recursively transform dict keys from snake_case to camelCase.

    Args:
        data: Input data (dict, list, or primitive type)
        skip_keys: Set of keys to skip transformation (e.g., {'_id', 'ISO_code'})

    Returns:
        Transformed data with camelCase keys

    Examples:
        >>> data = {"change_percent": 2.5, "high_price": 2700}
        >>> transform_dict_keys(data)
        {'changePercent': 2.5, 'highPrice': 2700}

        >>> data = {"user_info": {"first_name": "John", "last_name": "Doe"}}
        >>> transform_dict_keys(data)
        {'userInfo': {'firstName': 'John', 'lastName': 'Doe'}}
    """
    skip_keys = skip_keys or set()

    if isinstance(data, dict):
        return {
            (to_camel_case(k) if k not in skip_keys and '_' in k else k): transform_dict_keys(v, skip_keys)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [transform_dict_keys(item, skip_keys) for item in data]
    elif isinstance(data, datetime):
        # Convert datetime to ISO string
        return data.isoformat()
    else:
        return data


def wrap_response(data: Any, timestamp: datetime = None) -> Dict[str, Any]:
    """Wrap response in standard format with camelCase transformation.

    Args:
        data: Response data to wrap
        timestamp: Optional timestamp (defaults to current time)

    Returns:
        Standardized response format:
        {
            "data": <transformed_data>,
            "timestamp": <iso_timestamp>
        }

    Examples:
        >>> data = {"price": 2700, "change_percent": 2.5}
        >>> response = wrap_response(data)
        >>> "data" in response and "timestamp" in response
        True
        >>> response["data"]["changePercent"]
        2.5
    """
    transformed_data = transform_dict_keys(data)
    return {
        "data": transformed_data,
        "timestamp": (timestamp or datetime.utcnow()).isoformat()
    }


def transform_response_body(body: bytes) -> bytes:
    """Transform JSON response body from snake_case to camelCase.

    This is a utility for middleware to transform response bodies.

    Args:
        body: JSON response body as bytes

    Returns:
        Transformed JSON response body as bytes

    Raises:
        ValueError: If body is not valid JSON
    """
    import json

    try:
        data = json.loads(body)
        transformed = transform_dict_keys(data)
        return json.dumps(transformed).encode()
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON body: {e}") from e


# Backwards compatibility - keep snake_case for internal use
def to_snake_case(camel_str: str) -> str:
    """Convert camelCase string to snake_case.

    Useful for query parameters from frontend.

    Args:
        camel_str: String in camelCase format

    Returns:
        String in snake_case format

    Examples:
        >>> to_snake_case("changePercent")
        'change_percent'
        >>> to_snake_case("highPrice")
        'high_price'
    """
    import re
    # Insert underscore before capital letters
    snake_str = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str)
    return snake_str.lower()
