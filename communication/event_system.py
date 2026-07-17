"""
Event System
Simple publish/subscribe event bus for Stockei agents and teams.
"""

from typing import Any, Callable, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventSystem:
    """Publish/subscribe event bus with an event log."""

    def __init__(self) -> None:
        """Initialize empty subscriber map and event log."""
        self.subscribers: Dict[str, List[Callable[[Any], Any]]] = {}
        self.event_log: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str,
                  handler: Callable[[Any], Any]) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: Name of the event.
            handler: Callable invoked with the event payload.
        """
        self.subscribers.setdefault(event_type, []).append(handler)
        logger.info("EventSystem: subscribed handler to '%s'", event_type)

    def publish(self, event_type: str, payload: Any = None) -> List[Any]:
        """
        Publish an event to all subscribed handlers.

        Args:
            event_type: Name of the event.
            payload: Data passed to each handler.

        Returns:
            List of handler results (exceptions are logged and skipped).
        """
        self.event_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "payload": payload,
        })
        results: List[Any] = []
        for handler in self.subscribers.get(event_type, []):
            try:
                results.append(handler(payload))
            except Exception as exc:  # noqa: BLE001
                logger.error("EventSystem: handler error for '%s': %s",
                             event_type, exc)
        logger.info("EventSystem: published '%s' to %d handlers",
                    event_type, len(results))
        return results
