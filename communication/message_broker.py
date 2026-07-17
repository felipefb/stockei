"""
Message Broker
Central message hub for Stockei agents. Agents register themselves and
exchange direct or broadcast messages; every message is kept in history.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MessageBroker:
    """Routes messages between registered agents and records history."""

    def __init__(self) -> None:
        """Initialize the broker with empty registry and history."""
        self.agents: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

    def register(self, agent: Any) -> None:
        """
        Register an agent so it can receive messages.

        Args:
            agent: Object exposing a ``name`` attribute and, optionally,
                a ``receive_message(message)`` method.
        """
        self.agents[agent.name] = agent
        logger.info("MessageBroker: registered agent '%s'", agent.name)

    def send(self, from_agent: str, to_agent: str, content: Any,
             message_type: str = "info") -> Dict[str, Any]:
        """
        Send a direct message from one agent to another.

        Args:
            from_agent: Sender name.
            to_agent: Recipient name.
            content: Message payload.
            message_type: Semantic type of the message.

        Returns:
            The message dict (timestamp, from, to, type, content).
        """
        message: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "content": content,
        }
        self.history.append(message)
        recipient = self.agents.get(to_agent)
        if recipient is not None and hasattr(recipient, "receive_message"):
            recipient.receive_message(message)
        logger.info("MessageBroker: %s -> %s (%s)", from_agent, to_agent,
                    message_type)
        return message

    def broadcast(self, from_agent: str, content: Any,
                  message_type: str = "broadcast") -> List[Dict[str, Any]]:
        """
        Broadcast a message from an agent to all other registered agents.

        Args:
            from_agent: Sender name.
            content: Message payload.
            message_type: Semantic type of the message.

        Returns:
            List of the message dicts delivered.
        """
        messages: List[Dict[str, Any]] = []
        for name in list(self.agents):
            if name != from_agent:
                messages.append(
                    self.send(from_agent, name, content, message_type))
        logger.info("MessageBroker: broadcast from %s to %d agents",
                    from_agent, len(messages))
        return messages

    def get_history(self,
                    agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return message history, optionally filtered by agent.

        Args:
            agent_name: If given, only messages sent or received by
                this agent are returned.

        Returns:
            List of message dicts.
        """
        if agent_name is None:
            return list(self.history)
        return [m for m in self.history
                if m["from"] == agent_name or m["to"] == agent_name]
