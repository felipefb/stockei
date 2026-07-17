"""Design/UX Agent — user experience design for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agents.base.commercialization_agent import CommercializationAgent

logger = logging.getLogger(__name__)


class DesignUXAgent(CommercializationAgent):
    """Design/UX agent: screen design specs and usability reviews."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Design/UX agent."""
        super().__init__(name="Design/UX Agent", role="Product Designer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested design action."""
        action = context.get("action")
        if action == "design_screen":
            return self.design_screen(context.get("screen", ""),
                                      context.get("goal", ""))
        if action == "usability_review":
            return self.usability_review(context.get("heuristics", {}))
        return {"status": "no_action"}

    def design_screen(self, screen: str, goal: str) -> Dict[str, Any]:
        """Produce a design spec for a Stockei screen."""
        spec = {
            "screen": screen or "lista_de_produtos",
            "goal": goal or "visualizar e repor estoque rapidamente",
            "layout": ["search_bar", "filters", "data_table",
                       "low_stock_badge", "primary_cta"],
            "mobile_first": True,
            "design_tokens": {"primary": "#1E6FFF", "danger": "#E5484D"},
            "timestamp": datetime.now().isoformat(),
        }
        self.activities.append({"type": "design_screen", "spec": spec})
        logger.info("Design spec created for '%s'", spec["screen"])
        return {"status": "completed", "spec": spec}

    def usability_review(self, heuristics: Dict[str, bool]) -> Dict[str, Any]:
        """Review a screen against Nielsen-style usability heuristics."""
        checks = ["visibility_of_status", "error_prevention",
                  "recognition_over_recall", "consistency",
                  "clear_feedback"]
        failed = [c for c in checks if not heuristics.get(c, False)]
        score = round(100 * (len(checks) - len(failed)) / len(checks))
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "usability_review", "score": score})
        logger.info("Usability review score: %d", score)
        return {"status": "completed", "score": score,
                "failed_heuristics": failed}
