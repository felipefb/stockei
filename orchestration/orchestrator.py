"""
Stockei Orchestrator
Coordinates teams, delegates workflows and wires agent communication.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StockeiOrchestrator:
    """Top-level orchestrator coordinating all Stockei teams."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the orchestrator.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        self.teams: Dict[str, Any] = {}
        self.workflows: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        logger.info("StockeiOrchestrator initialized")

    def register_team(self, team_name: str, team: Any) -> None:
        """
        Register a team under a name.

        Args:
            team_name: Key used to route workflows to the team.
            team: Team instance (TeamBase-compatible).
        """
        self.teams[team_name] = team
        logger.info("Orchestrator: registered team '%s'", team_name)

    def execute_workflow(self, workflow_name: str,
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow by delegating to the team named in the context.

        Args:
            workflow_name: Workflow identifier.
            context: Execution context; ``context["team"]`` selects the
                team and ``context.get("steps", [])`` provides its steps.

        Returns:
            Workflow record dict with results (or error if team unknown).
        """
        team_name = context.get("team")
        record: Dict[str, Any] = {
            "workflow": workflow_name,
            "team": team_name,
            "timestamp": datetime.now().isoformat(),
        }
        team = self.teams.get(team_name)
        if team is None:
            record["status"] = "error"
            record["error"] = f"team '{team_name}' not registered"
            logger.error("Orchestrator: %s", record["error"])
        else:
            steps = context.get("steps", [])
            record["results"] = team.execute_workflow(steps)
            record["status"] = "completed"
            logger.info("Orchestrator: workflow '%s' executed by team '%s'",
                        workflow_name, team_name)
        self.workflows.append(record)
        return record

    def register_agent_communication(self, broker: Any,
                                     event_system: Any) -> int:
        """
        Attach communication infrastructure to all agents of all teams.

        Args:
            broker: MessageBroker instance.
            event_system: EventSystem instance.

        Returns:
            Number of agents wired.
        """
        count = 0
        for team in self.teams.values():
            for agent in getattr(team, "agents", {}).values():
                agent.attach_communication(broker, event_system)
                if hasattr(broker, "register"):
                    broker.register(agent)
                count += 1
        logger.info("Orchestrator: communication attached to %d agents",
                    count)
        return count

    def get_status(self) -> Dict[str, Any]:
        """
        Return orchestrator status.

        Returns:
            Dict with created_at, teams_count, workflows_executed and
            per-team status.
        """
        teams_status: Dict[str, Any] = {}
        for name, team in self.teams.items():
            try:
                teams_status[name] = team.get_team_status()
            except Exception as exc:  # noqa: BLE001
                teams_status[name] = {"error": str(exc)}
        return {
            "created_at": self.created_at.isoformat(),
            "teams_count": len(self.teams),
            "workflows_executed": len(self.workflows),
            "teams": teams_status,
        }
