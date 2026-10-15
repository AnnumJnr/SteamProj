"""
General utility functions used across the platform.
Only truly shared, stateless helpers belong here.
App-specific utilities belong in the respective app.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_get(dictionary: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely retrieve a nested value from a dictionary without raising KeyError.

    Example:
        safe_get(data, "provider", "name", default="Unknown")
    """
    value = dictionary
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key, default)
    return value


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to max_length characters, appending suffix if truncated.
    Used when storing descriptions from external sources that may be too long.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def build_full_url(base_url: str, path: str) -> str:
    """
    Join a base URL and a path, ensuring exactly one slash between them.
    Used when constructing URLs for external API calls.
    """
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"