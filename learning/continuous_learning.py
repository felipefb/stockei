"""
Continuous Learning
Aggregates learnings across agents and runs feedback-driven
learning cycles.
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

from learning.feedback_system import FeedbackSystem

logger = logging.getLogger(__name__)


class ContinuousLearning:
    """Coordinates the continuous learning loop across all agents."""

    def __init__(self) -> None:
        """Initialize agent registry and internal feedback system."""
        self.agents: Dict[str, Any] = {}
        self.feedback_system = FeedbackSystem()
        self.cycles: List[Dict[str, Any]] = []

    def register_agent(self, agent: Any) -> None:
        """
        Register an agent in the learning loop.

        Args:
            agent: Agent exposing ``name``, ``export_learning`` and
                ``learn_from_feedback``.
        """
        self.agents[agent.name] = agent
        logger.info("ContinuousLearning: registered '%s'", agent.name)

    def collect_learnings(self) -> Dict[str, Any]:
        """
        Aggregate ``export_learning()`` from all registered agents.

        Returns:
            Dict mapping agent name to its exported learning.
        """
        learnings: Dict[str, Any] = {}
        for name, agent in self.agents.items():
            try:
                learnings[name] = agent.export_learning()
            except Exception as exc:  # noqa: BLE001
                logger.error("ContinuousLearning: export failed for '%s': %s",
                             name, exc)
                learnings[name] = {"error": str(exc)}
        return learnings

    def learning_cycle(
            self, feedback_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply feedback per agent and return a cycle summary.

        Args:
            feedback_map: Mapping agent name -> feedback dict.

        Returns:
            Summary dict with applied feedback, skipped agents and
            aggregated learnings.
        """
        applied: List[str] = []
        skipped: List[str] = []
        for name, feedback in feedback_map.items():
            agent = self.agents.get(name)
            if agent is None:
                skipped.append(name)
                logger.warning("ContinuousLearning: unknown agent '%s'", name)
                continue
            self.feedback_system.submit_feedback(agent, feedback)
            applied.append(name)
        summary: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "applied": applied,
            "skipped": skipped,
            "learnings": self.collect_learnings(),
        }
        self.cycles.append(summary)
        logger.info("ContinuousLearning: cycle applied to %d agents",
                    len(applied))
        return summary
