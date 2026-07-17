"""Frontend Engineer Agent — UI implementation for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.execution_agent import ExecutionAgent

logger = logging.getLogger(__name__)


class FrontendEngineerAgent(ExecutionAgent):
    """Frontend Engineer agent: builds UI screens and checks accessibility."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Frontend Engineer agent."""
        super().__init__(name="Frontend Engineer Agent",
                         role="Frontend Engineer", config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested frontend action."""
        action = context.get("action")
        if action == "build_ui":
            return self.build_ui(context.get("screen", ""),
                                 context.get("components", []))
        if action == "accessibility_check":
            return self.accessibility_check(context.get("audit", {}))
        return {"status": "no_action"}

    def build_ui(self, screen: str,
                 components: List[str]) -> Dict[str, Any]:
        """Plan a UI screen build (e.g., product list, stock dashboard)."""
        defaults = ["header", "loading_state", "empty_state", "error_state"]
        plan = {
            "screen": screen or "dashboard_estoque",
            "components": sorted(set(components) | set(defaults)),
            "responsive": True,
            "i18n": "pt-BR",
        }
        self.tasks.append({"type": "build_ui", "plan": plan,
                           "timestamp": datetime.now().isoformat()})
        logger.info("Frontend planned screen '%s'", plan["screen"])
        return {"status": "completed", "ui_plan": plan}

    def accessibility_check(self, audit: Dict[str, Any]) -> Dict[str, Any]:
        """Check basic WCAG criteria from an audit payload."""
        issues = []
        if audit.get("contrast_ratio", 4.5) < 4.5:
            issues.append("Insufficient color contrast (<4.5:1)")
        if not audit.get("alt_texts", True):
            issues.append("Images missing alt text")
        if not audit.get("keyboard_navigable", True):
            issues.append("Not fully keyboard navigable")
        if not audit.get("labels_on_inputs", True):
            issues.append("Form inputs missing labels")
        score = max(0, 100 - 25 * len(issues))
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "accessibility_check", "score": score})
        logger.info("Frontend a11y score: %d", score)
        return {"status": "completed", "score": score, "issues": issues}
