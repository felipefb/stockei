"""
Workflow Manager
Defines named workflows and runs them through the orchestrator or
directly against teams.
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Registry and runner for named Stockei workflows."""

    def __init__(self) -> None:
        """Initialize the workflow registry."""
        self.workflows: Dict[str, List[Dict[str, Any]]] = {}

    def define_workflow(self, name: str,
                        steps: List[Dict[str, Any]]) -> None:
        """
        Define (or redefine) a named workflow.

        Args:
            name: Workflow name.
            steps: List of step dicts ({"agent": ..., "context": {...}}).
        """
        self.workflows[name] = steps
        logger.info("WorkflowManager: defined workflow '%s' (%d steps)",
                    name, len(steps))

    def list_workflows(self) -> List[str]:
        """
        List defined workflow names.

        Returns:
            List of workflow names.
        """
        return list(self.workflows)

    def run(self, name: str, executor: Any,
            context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a defined workflow.

        Args:
            name: Workflow name previously defined.
            executor: A StockeiOrchestrator (has ``execute_workflow``
                with name+context) or a TeamBase-like team (has
                ``execute_workflow`` with steps).
            context: Execution context; for orchestrators it should
                include ``"team"``.

        Returns:
            Result dict from the executor.

        Raises:
            KeyError: If the workflow is not defined.
        """
        if name not in self.workflows:
            raise KeyError(f"Workflow '{name}' is not defined")
        steps = self.workflows[name]
        logger.info("WorkflowManager: running workflow '%s'", name)
        if hasattr(executor, "register_team"):  # orchestrator
            full_context = dict(context)
            full_context.setdefault("steps", steps)
            return executor.execute_workflow(name, full_context)
        # team-like executor
        results = executor.execute_workflow(steps)
        return {
            "workflow": name,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": results,
        }
