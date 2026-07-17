"""
Team Base
Base class for Stockei agent teams. A team groups agents and runs
workflows composed of per-agent steps.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TeamBase:
    """Base class for a team of Stockei agents."""

    def __init__(self, name: str,
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the team.

        Args:
            name: Team name.
            agents: Initial list of agents.
        """
        self.name = name
        self.agents: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.executions: List[Dict[str, Any]] = []
        for agent in agents or []:
            self.add_agent(agent)
        logger.info("Team '%s' created with %d agents",
                    self.name, len(self.agents))

    def add_agent(self, agent: Any) -> None:
        """
        Add an agent to the team.

        Args:
            agent: Agent exposing ``name`` and ``execute(context)``.
        """
        self.agents[agent.name] = agent
        logger.info("Team '%s': added agent '%s'", self.name, agent.name)

    def execute_workflow(
            self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a workflow of steps within the team.

        Each step is ``{"agent": <agent name>, "context": {...}}`` and
        invokes ``agent.execute(context)``.

        Args:
            steps: Ordered list of step dicts.

        Returns:
            List of step results with agent name, status and result/error.
        """
        results: List[Dict[str, Any]] = []
        for step in steps:
            agent_name = step.get("agent")
            context = step.get("context", {})
            agent = self.agents.get(agent_name)
            if agent is None:
                logger.warning("Team '%s': unknown agent '%s' in step",
                               self.name, agent_name)
                results.append({"agent": agent_name, "status": "skipped",
                                "error": "agent not found"})
                continue
            try:
                result = agent.execute(context)
                results.append({"agent": agent_name, "status": "ok",
                                "result": result})
                logger.info("Team '%s': step executed by '%s'",
                            self.name, agent_name)
            except Exception as exc:  # noqa: BLE001
                logger.error("Team '%s': step failed for '%s': %s",
                             self.name, agent_name, exc)
                results.append({"agent": agent_name, "status": "error",
                                "error": str(exc)})
        self.executions.append({
            "timestamp": datetime.now().isoformat(),
            "steps": len(steps),
            "results": results,
        })
        return results

    def get_team_status(self) -> Dict[str, Any]:
        """
        Return the team status.

        Returns:
            Dict with name, agent count, agent statuses and executions.
        """
        agent_statuses: Dict[str, Any] = {}
        for name, agent in self.agents.items():
            try:
                agent_statuses[name] = agent.get_status()
            except Exception as exc:  # noqa: BLE001
                agent_statuses[name] = {"error": str(exc)}
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "agents_count": len(self.agents),
            "agents": agent_statuses,
            "workflows_executed": len(self.executions),
        }
