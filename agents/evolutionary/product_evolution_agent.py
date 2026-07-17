"""Product Evolution Agent — usage-driven product improvement for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.evolutionary_agent import EvolutionaryAgent

logger = logging.getLogger(__name__)


class ProductEvolutionAgent(EvolutionaryAgent):
    """Product Evolution agent: analyzes feature usage and proposes features."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Product Evolution agent."""
        super().__init__(name="Product Evolution Agent",
                         role="Product Evolution Analyst", config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested evolution action."""
        action = context.get("action")
        if action == "analyze_usage":
            return self.analyze_usage(context.get("feature_usage", {}))
        if action == "propose_features":
            return self.propose_features(context.get("signals", []))
        return {"status": "no_action"}

    def analyze_usage(self, feature_usage: Dict[str, int]) -> Dict[str, Any]:
        """Classify features as core, growing or underused by usage counts."""
        total = sum(feature_usage.values()) or 1
        analysis = {}
        for feature, count in feature_usage.items():
            share = count / total
            tier = ("core" if share >= 0.3 else
                    "growing" if share >= 0.1 else "underused")
            analysis[feature] = {"usage": count, "share": round(share, 3),
                                 "tier": tier}
        underused = [f for f, a in analysis.items() if a["tier"] == "underused"]
        self.insights.append({"type": "usage_analysis", "analysis": analysis,
                              "timestamp": datetime.now().isoformat()})
        logger.info("Evolution usage analysis: %d features", len(analysis))
        return {"status": "completed", "analysis": analysis,
                "improve_or_sunset": underused}

    def propose_features(self,
                         signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Turn customer signals into ranked feature proposals."""
        proposals = []
        for signal in signals:
            weight = signal.get("requests", 1) * signal.get("revenue_impact", 1)
            proposals.append({"feature": signal.get("feature", "unknown"),
                              "score": weight,
                              "source": signal.get("source", "feedback")})
        proposals.sort(key=lambda p: p["score"], reverse=True)
        if not proposals:
            proposals = [{"feature": "Integracao com marketplaces",
                          "score": 1, "source": "default_hypothesis"}]
        self.insights.append({"type": "feature_proposals",
                              "proposals": proposals,
                              "timestamp": datetime.now().isoformat()})
        logger.info("Evolution proposed %d features", len(proposals))
        return {"status": "completed", "proposals": proposals}
