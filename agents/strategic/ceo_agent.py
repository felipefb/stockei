"""CEO Agent — top-level strategic oversight for Stockei (inventory SaaS)."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agents.base.strategic_agent import StrategicAgent

logger = logging.getLogger(__name__)


class CEOAgent(StrategicAgent):
    """Chief Executive Officer agent: monitors KPIs, runs quarterly reviews
    and records strategic decisions for Stockei."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the CEO agent with default KPI targets."""
        super().__init__(name="CEO Agent", role="Chief Executive Officer",
                         config=config or {})
        self.kpi_targets: Dict[str, float] = {
            "arr": 5_000_000,
            "churn_rate": 0.05,
            "cac": 500,
            "ltv": 10_000,
            "market_share": 0.15,
        }
        self.quarterly_reviews: list = []

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested action based on context['action']."""
        action = context.get("action")
        if action == "monitor_kpis":
            return self.monitor_kpis(
                context.get("metrics", context.get("current_kpis", {})))
        if action == "quarterly_review":
            return self.quarterly_review(context.get("quarter", "Q?"),
                                         context.get("data", {}))
        if action == "strategic_decision":
            return self.strategic_decision(context.get("topic", ""),
                                           context.get("options", []))
        return {"status": "no_action"}

    def monitor_kpis(self, current_kpis: Dict[str, float]) -> Dict[str, Any]:
        """Compare current KPIs against targets and produce a health status
        with recommended actions."""
        variances: Dict[str, float] = {}
        for kpi, target in self.kpi_targets.items():
            current = current_kpis.get(kpi)
            if current is None or not target:
                continue
            if kpi in ("churn_rate", "cac"):
                # Lower is better: positive variance means below target.
                variances[kpi] = (target - current) / target
            else:
                variances[kpi] = (current - target) / target

        avg_variance = (sum(variances.values()) / len(variances)) if variances else 0.0
        if avg_variance > 0.1:
            health_status = "EXCELLENT"
        elif avg_variance > -0.1:
            health_status = "GOOD"
        elif avg_variance > -0.2:
            health_status = "WARNING"
        else:
            health_status = "CRITICAL"

        actions = []
        if current_kpis.get("churn_rate", 0) > self.kpi_targets["churn_rate"]:
            actions.append("Increase Customer Success focus")
        if current_kpis.get("cac", 0) > self.kpi_targets["cac"]:
            actions.append("Optimize marketing campaigns")
        if current_kpis.get("arr", 0) < 0.8 * self.kpi_targets["arr"]:
            actions.append("Increase sales effort")

        result = {
            "status": "completed",
            "health_status": health_status,
            "avg_variance": round(avg_variance, 4),
            "variances": {k: round(v, 4) for k, v in variances.items()},
            "actions": actions,
        }
        self.learning_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "monitor_kpis",
            "result": result,
        })
        logger.info("CEO KPI health: %s", health_status)
        return result

    def quarterly_review(self, quarter: str,
                         data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a quarterly business review and store it."""
        review = {
            "quarter": quarter,
            "timestamp": datetime.now().isoformat(),
            "highlights": data.get("highlights", []),
            "lowlights": data.get("lowlights", []),
            "kpi_snapshot": data.get("kpis", {}),
            "next_quarter_focus": data.get(
                "focus", ["Grow ARR", "Reduce churn", "Ship roadmap"]),
        }
        self.quarterly_reviews.append(review)
        self.strategic_reviews.append(review)
        logger.info("CEO quarterly review recorded for %s", quarter)
        return {"status": "completed", "review": review}

    def strategic_decision(self, topic: str, options: list) -> Dict[str, Any]:
        """Choose the option with the highest declared score and record it."""
        best = None
        if options:
            best = max(options, key=lambda o: o.get("score", 0)
                       if isinstance(o, dict) else 0)
        decision = self.record_decision({
            "type": "strategic_decision",
            "topic": topic,
            "options_considered": len(options),
            "chosen": best,
        })
        logger.info("CEO strategic decision on '%s'", topic)
        return {"status": "completed", "decision": decision}
