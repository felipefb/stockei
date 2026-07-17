"""
Agent Base Class
Common foundation for all Stockei agents.
Replicates the pattern from agent_team_app (AgentBase inheritance,
learning loop, feedback system).
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class AgentBase(ABC):
    """
    Base class for every Stockei agent.

    Patterns replicated from agent_team_app:
    1. Inheritance: all agents inherit from AgentBase
    2. Communication: via message_broker and event_system
    3. Learning: feedback loop with learning_system
    4. Configuration: YAML with agent list
    5. Orchestration: Orchestrator coordinates teams
    """

    category: str = "generic"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize agent.

        Args:
            name: Agent name (e.g., "CEO Agent")
            role: Agent role (e.g., "Chief Executive Officer")
            config: Configuration dictionary
        """
        self.name = name
        self.role = role
        self.config = config or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Learning system (replicating agent_team_app pattern)
        self.learning_history: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        self.feedback: List[Dict[str, Any]] = []

        # State
        self.state: Dict[str, Any] = {}
        self.metrics: Dict[str, float] = {}

        # Communication (attached by orchestrator/team)
        self.broker = None
        self.event_system = None

        logger.info(f"Initialized {self.name} ({self.role})")

    # ------------------------------------------------------------------ #
    # Core execution
    # ------------------------------------------------------------------ #
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent's main responsibility.
        Must be implemented by subclasses.
        """

    # ------------------------------------------------------------------ #
    # Learning loop
    # ------------------------------------------------------------------ #
    def learn_from_feedback(self, feedback: Dict[str, Any]) -> None:
        """Learn from feedback (replicating agent_team_app pattern)."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "processed": False,
        }
        self.feedback.append(record)
        self._process_feedback(feedback)
        record["processed"] = True
        self.updated_at = datetime.now()
        logger.info(f"{self.name} learned from feedback")

    def _process_feedback(self, feedback: Dict[str, Any]) -> None:
        """Process and integrate feedback into agent's knowledge."""
        self.learning_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "feedback",
            "content": feedback,
        })

    def record_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Record a decision with timestamp."""
        decision.setdefault("timestamp", datetime.now().isoformat())
        self.decisions.append(decision)
        return decision

    # ------------------------------------------------------------------ #
    # Communication
    # ------------------------------------------------------------------ #
    def attach_communication(self, broker=None, event_system=None) -> None:
        """Attach message broker and event system."""
        if broker is not None:
            self.broker = broker
            broker.register(self)
        if event_system is not None:
            self.event_system = event_system

    def send_message(self, to_agent: str, content: Any,
                     message_type: str = "info") -> Optional[Dict[str, Any]]:
        """Send a message to another agent via broker."""
        if self.broker is None:
            logger.warning(f"{self.name} has no broker attached")
            return None
        return self.broker.send(self.name, to_agent, content, message_type)

    def receive_message(self, message: Dict[str, Any]) -> None:
        """Handle an incoming message. Subclasses may override."""
        self.learning_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "message_received",
            "content": message,
        })

    # ------------------------------------------------------------------ #
    # Status / export
    # ------------------------------------------------------------------ #
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "name": self.name,
            "role": self.role,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "decisions_count": len(self.decisions),
            "feedback_count": len(self.feedback),
            "learning_records": len(self.learning_history),
        }

    def export_learning(self) -> Dict[str, Any]:
        """Export learning history."""
        return {
            "agent": self.name,
            "role": self.role,
            "learning_history": self.learning_history,
            "decisions": self.decisions,
            "feedback": self.feedback,
        }
