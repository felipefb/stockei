"""Marketing Agent — growth marketing for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.commercialization_agent import CommercializationAgent

logger = logging.getLogger(__name__)


class MarketingAgent(CommercializationAgent):
    """Marketing agent: campaign planning, content calendar and CAC reporting."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Marketing agent."""
        super().__init__(name="Marketing Agent", role="Marketing Manager",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested marketing action."""
        action = context.get("action")
        if action == "campaign_plan":
            return self.campaign_plan(context.get("goal", "leads"),
                                      context.get("budget_brl", 5000.0))
        if action == "content_calendar":
            return self.content_calendar(context.get("weeks", 4))
        if action == "cac_report":
            return self.cac_report(context.get("spend_brl", 0.0),
                                   context.get("new_customers", 0))
        return {"status": "no_action"}

    def campaign_plan(self, goal: str, budget_brl: float) -> Dict[str, Any]:
        """Split budget across channels for a campaign goal."""
        split = {"google_ads": 0.4, "meta_ads": 0.3, "content_seo": 0.2,
                 "partnerships": 0.1}
        channels = {ch: round(budget_brl * pct, 2) for ch, pct in split.items()}
        plan = {"goal": goal, "budget_brl": budget_brl, "channels": channels,
                "audience": "small retailers and e-commerce in Brazil",
                "timestamp": datetime.now().isoformat()}
        self.activities.append({"type": "campaign_plan", "plan": plan})
        logger.info("Marketing campaign planned: %s (R$%.2f)", goal, budget_brl)
        return {"status": "completed", "campaign": plan}

    def content_calendar(self, weeks: int = 4) -> Dict[str, Any]:
        """Generate a rotating weekly content calendar."""
        topics = ["Como evitar ruptura de estoque",
                  "Ponto de pedido: quando repor",
                  "Curva ABC para pequenos negocios",
                  "Reduza perdas com alertas de estoque baixo"]
        calendar = [{"week": w + 1, "topic": topics[w % len(topics)],
                     "format": "blog+social"} for w in range(weeks)]
        self.activities.append({"type": "content_calendar",
                                "calendar": calendar,
                                "timestamp": datetime.now().isoformat()})
        logger.info("Marketing content calendar: %d weeks", weeks)
        return {"status": "completed", "calendar": calendar}

    def cac_report(self, spend_brl: float,
                   new_customers: int) -> Dict[str, Any]:
        """Compute CAC in R$ and flag if above target."""
        cac = spend_brl / new_customers if new_customers else None
        target = self.config.get("cac_target_brl", 500.0)
        above_target = cac is not None and cac > target
        report = {"status": "completed", "spend_brl": spend_brl,
                  "new_customers": new_customers,
                  "cac_brl": round(cac, 2) if cac is not None else None,
                  "target_brl": target, "above_target": above_target}
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "cac_report", "report": report})
        logger.info("Marketing CAC: %s", report["cac_brl"])
        return report
