"""Product Manager Agent — product planning for Stockei (inventory SaaS)."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.planning_agent import PlanningAgent

logger = logging.getLogger(__name__)


class ProductManagerAgent(PlanningAgent):
    """Product Manager agent: RICE backlog prioritization, PRDs and roadmap."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Product Manager agent."""
        super().__init__(name="Product Manager Agent", role="Product Manager",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested product action."""
        action = context.get("action")
        if action == "prioritize_backlog":
            return self.prioritize_backlog(context.get("backlog", []))
        if action == "write_prd":
            return self.write_prd(context.get("feature", {}))
        if action == "roadmap":
            return self.roadmap(context.get("items", []))
        return {"status": "no_action"}

    def prioritize_backlog(self,
                           backlog: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rank backlog items by RICE score (reach*impact*confidence/effort)."""
        ranked = []
        for item in backlog:
            reach = item.get("reach", 1)
            impact = item.get("impact", 1)
            confidence = item.get("confidence", 0.5)
            effort = max(item.get("effort", 1), 0.1)
            rice = reach * impact * confidence / effort
            ranked.append({**item, "rice_score": round(rice, 2)})
        ranked.sort(key=lambda i: i["rice_score"], reverse=True)
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "prioritize_backlog", "items": len(ranked)})
        logger.info("PM prioritized %d backlog items", len(ranked))
        return {"status": "completed", "prioritized_backlog": ranked}

    def write_prd(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a lightweight PRD skeleton for a feature."""
        prd = {
            "title": feature.get("name", "Untitled feature"),
            "problem": feature.get("problem",
                                   "Small businesses lose money on stockouts"),
            "target_users": feature.get("users", ["small retail owners"]),
            "success_metrics": feature.get(
                "metrics", ["adoption_rate", "stockout_reduction"]),
            "requirements": feature.get("requirements", []),
            "created_at": datetime.now().isoformat(),
        }
        self.plans.append({"type": "prd", "prd": prd})
        logger.info("PM wrote PRD for '%s'", prd["title"])
        return {"status": "completed", "prd": prd}

    def roadmap(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bucket items into Now / Next / Later based on priority."""
        buckets: Dict[str, List[Dict[str, Any]]] = {"now": [], "next": [],
                                                    "later": []}
        for item in items:
            priority = item.get("priority", "low")
            if priority == "high":
                buckets["now"].append(item)
            elif priority == "medium":
                buckets["next"].append(item)
            else:
                buckets["later"].append(item)
        self.plans.append({"type": "roadmap", "roadmap": buckets,
                           "timestamp": datetime.now().isoformat()})
        logger.info("PM roadmap built (%d items)", len(items))
        return {"status": "completed", "roadmap": buckets}
