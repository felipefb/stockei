"""
Helpers
Small general-purpose utilities for Stockei.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import uuid


def timestamp() -> str:
    """
    Return the current time as an ISO-8601 string.

    Returns:
        ISO formatted timestamp.
    """
    return datetime.now().isoformat()


def gen_id(prefix: str = "stk") -> str:
    """
    Generate a short unique identifier.

    Args:
        prefix: String prefix for the identifier.

    Returns:
        Identifier like ``stk-1a2b3c4d``.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def safe_get(data: Dict[str, Any], path: str,
             default: Optional[Any] = None) -> Any:
    """
    Safely navigate a nested dict using a dotted path.

    Args:
        data: Source dictionary.
        path: Dotted key path, e.g. ``"llm.model"``.
        default: Value returned when the path is missing.

    Returns:
        The value at the path, or ``default``.
    """
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current
