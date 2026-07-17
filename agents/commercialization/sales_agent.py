"""Sales Agent — sales pipeline for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.commercialization_agent import CommercializationAgent

logger = logging.getLogger(__name__)


class SalesAgent(CommercializationAgent):
    """Sales agent: lead qualification, pipeline reporting and deal closing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Sales agent."""
        super().__init__(name="Sales Agent", role="Sales Representative",
                         config=config or {})
        self.pipeline: List[Dict[str, Any]] = []

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested sales action."""
        action = context.get("action")
        if action == "qualify_lead":
            return self.qualify_lead(context.get("lead", {}))
        if action == "pipeline_report":
            return self.pipeline_report()
        if action == "close_deal":
            return self.close_deal(context.get("deal", {}))
        return {"status": "no_action"}

    def qualify_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Score a lead using a simple BANT-style checklist."""
        score = 0
        if lead.get("has_budget"):
            score += 25
        if lead.get("decision_maker"):
            score += 25
        if lead.get("manages_inventory"):
            score += 30
        if lead.get("timeline_days", 999) <= 90:
            score += 20
        qualified = score >= 60
        entry = {"lead": lead.get("name", "unknown"), "score": score,
                 "qualified": qualified, "stage": "qualified" if qualified
                 else "nurture", "timestamp": datetime.now().isoformat()}
        self.pipeline.append(entry)
        self.activities.append({"type": "qualify_lead", **entry})
        logger.info("Sales lead '%s' score=%d", entry["lead"], score)
        return {"status": "completed", **entry}

    def pipeline_report(self) -> Dict[str, Any]:
        """Summarize the pipeline by stage."""
        by_stage: Dict[str, int] = {}
        for deal in self.pipeline:
            stage = deal.get("stage", "unknown")
            by_stage[stage] = by_stage.get(stage, 0) + 1
        report = {"status": "completed", "total_deals": len(self.pipeline),
                  "by_stage": by_stage}
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "pipeline_report", "report": report})
        logger.info("Sales pipeline report: %d deals", len(self.pipeline))
        return report

    def close_deal(self, deal: Dict[str, Any]) -> Dict[str, Any]:
        """Close a deal and record its monthly value in R$."""
        entry = {"lead": deal.get("name", "unknown"),
                 "plan": deal.get("plan", "Starter"),
                 "mrr_brl": deal.get("mrr_brl", 49.90),
                 "stage": "closed_won",
                 "timestamp": datetime.now().isoformat()}
        self.pipeline.append(entry)
        self.record_decision({"type": "close_deal", "deal": entry})
        logger.info("Sales closed deal '%s' (%s)", entry["lead"], entry["plan"])
        return {"status": "completed", "deal": entry}
