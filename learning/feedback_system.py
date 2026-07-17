"""
Feedback System
Delivers feedback to agents and keeps a record for later analysis.
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FeedbackSystem:
    """Collects and delivers feedback to Stockei agents."""

    def __init__(self) -> None:
        """Initialize the feedback record list."""
        self.records: List[Dict[str, Any]] = []

    def submit_feedback(self, agent: Any,
                        feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deliver feedback to an agent and store a record.

        Args:
            agent: Agent exposing ``learn_from_feedback(feedback)``.
            feedback: Feedback payload.

        Returns:
            The stored record dict.
        """
        agent.learn_from_feedback(feedback)
        record: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "agent": getattr(agent, "name", str(agent)),
            "feedback": feedback,
        }
        self.records.append(record)
        logger.info("FeedbackSystem: feedback delivered to '%s'",
                    record["agent"])
        return record

    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        Summarize collected feedback.

        Returns:
            Dict with total count and per-agent counts.
        """
        per_agent: Dict[str, int] = {}
        for rec in self.records:
            per_agent[rec["agent"]] = per_agent.get(rec["agent"], 0) + 1
        return {"total": len(self.records), "by_agent": per_agent}
