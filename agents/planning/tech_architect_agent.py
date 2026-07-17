"""Tech Architect Agent — architecture design for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agents.base.planning_agent import PlanningAgent

logger = logging.getLogger(__name__)


class TechArchitectAgent(PlanningAgent):
    """Technical Architect agent: designs and reviews system architecture."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Tech Architect agent."""
        super().__init__(name="Tech Architect Agent",
                         role="Technical Architect", config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested architecture action."""
        action = context.get("action")
        if action == "design_architecture":
            return self.design_architecture(context.get("requirements", {}))
        if action == "review_design":
            return self.review_design(context.get("design", {}))
        return {"status": "no_action"}

    def design_architecture(self,
                            requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Propose an architecture based on expected scale."""
        expected_users = requirements.get("expected_users", 1000)
        style = "modular_monolith" if expected_users < 50_000 else "microservices"
        design = {
            "style": style,
            "components": ["api_gateway", "auth_service", "inventory_core",
                           "alerts_worker", "reporting"],
            "database": "PostgreSQL",
            "cache": "Redis" if expected_users > 5000 else None,
            "queue": "RabbitMQ" if style == "microservices" else "in-process",
            "created_at": datetime.now().isoformat(),
        }
        self.plans.append({"type": "architecture", "design": design})
        logger.info("Architect designed %s architecture", style)
        return {"status": "completed", "design": design}

    def review_design(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Review a design for common gaps (auth, backup, observability)."""
        issues = []
        components = design.get("components", [])
        if "auth_service" not in components and not design.get("auth"):
            issues.append("Missing authentication component")
        if not design.get("backup_strategy"):
            issues.append("Missing backup strategy")
        if not design.get("observability"):
            issues.append("Missing observability (logs/metrics/traces)")
        approved = not issues
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "review_design", "approved": approved})
        logger.info("Architect design review: approved=%s", approved)
        return {"status": "completed", "approved": approved, "issues": issues}
