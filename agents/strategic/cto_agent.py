"""CTO Agent — technology strategy for Stockei (inventory SaaS)."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.strategic_agent import StrategicAgent

logger = logging.getLogger(__name__)


class CTOAgent(StrategicAgent):
    """Chief Technology Officer agent: tech roadmap, stack evaluation
    and incident reviews."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the CTO agent."""
        super().__init__(name="CTO Agent", role="Chief Technology Officer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested technology action."""
        action = context.get("action")
        if action == "tech_roadmap":
            return self.tech_roadmap(context.get("initiatives", []))
        if action == "evaluate_stack":
            return self.evaluate_stack(context.get("candidates", []))
        if action == "incident_review":
            return self.incident_review(context.get("incident", {}))
        return {"status": "no_action"}

    def tech_roadmap(self, initiatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Order initiatives by impact/effort ratio into a quarterly roadmap."""
        scored = []
        for item in initiatives:
            impact = item.get("impact", 1)
            effort = max(item.get("effort", 1), 1)
            scored.append({**item, "priority_score": round(impact / effort, 2)})
        scored.sort(key=lambda i: i["priority_score"], reverse=True)
        roadmap = [{"quarter": f"Q{(idx // 3) + 1}", **item}
                   for idx, item in enumerate(scored)]
        result = {"status": "completed", "roadmap": roadmap}
        self.strategic_reviews.append(
            {"timestamp": datetime.now().isoformat(),
             "type": "tech_roadmap", "items": len(roadmap)})
        logger.info("CTO roadmap generated with %d initiatives", len(roadmap))
        return result

    def evaluate_stack(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Score stack candidates on maturity, team fit and cost (1-5 each)."""
        evaluations = []
        for cand in candidates:
            score = (cand.get("maturity", 3) + cand.get("team_fit", 3)
                     + cand.get("cost_efficiency", 3)) / 3
            evaluations.append({"name": cand.get("name", "unknown"),
                                "score": round(score, 2)})
        evaluations.sort(key=lambda e: e["score"], reverse=True)
        chosen = evaluations[0] if evaluations else None
        self.record_decision({"type": "evaluate_stack", "chosen": chosen})
        logger.info("CTO stack evaluation: chosen=%s", chosen)
        return {"status": "completed", "evaluations": evaluations,
                "recommended": chosen}

    def incident_review(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Classify an incident's severity and produce follow-up actions."""
        downtime = incident.get("downtime_minutes", 0)
        if downtime > 60:
            severity = "SEV1"
        elif downtime > 15:
            severity = "SEV2"
        else:
            severity = "SEV3"
        actions = ["Write blameless postmortem"]
        if severity == "SEV1":
            actions += ["Add automated rollback", "Review on-call escalation"]
        review = {"status": "completed", "severity": severity,
                  "downtime_minutes": downtime, "actions": actions}
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "incident_review", "result": review})
        logger.info("CTO incident review: %s", severity)
        return review
