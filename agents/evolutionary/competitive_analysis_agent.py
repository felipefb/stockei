"""Competitive Analysis Agent — competitor tracking for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.evolutionary_agent import EvolutionaryAgent

logger = logging.getLogger(__name__)


class CompetitiveAnalysisAgent(EvolutionaryAgent):
    """Competitive Analysis agent: competitor matrices and positioning."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Competitive Analysis agent."""
        super().__init__(name="Competitive Analysis Agent",
                         role="Competitive Intelligence Analyst",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested competitive action."""
        action = context.get("action")
        if action == "competitor_matrix":
            return self.competitor_matrix(context.get("competitors", []))
        if action == "positioning":
            return self.positioning(context.get("matrix", []))
        return {"status": "no_action"}

    def competitor_matrix(self,
                          competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a feature/price comparison matrix (scores 1-5 per axis)."""
        axes = ["price_value", "ease_of_use", "inventory_features",
                "integrations", "support_pt_br"]
        matrix = []
        for comp in competitors:
            scores = {axis: comp.get(axis, 3) for axis in axes}
            matrix.append({"name": comp.get("name", "unknown"),
                           "scores": scores,
                           "total": sum(scores.values())})
        matrix.sort(key=lambda c: c["total"], reverse=True)
        self.insights.append({"type": "competitor_matrix", "matrix": matrix,
                              "timestamp": datetime.now().isoformat()})
        logger.info("Competitor matrix built: %d competitors", len(matrix))
        return {"status": "completed", "axes": axes, "matrix": matrix}

    def positioning(self, matrix: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Suggest a positioning angle based on competitors' weakest axes."""
        weakness_count: Dict[str, int] = {}
        for comp in matrix:
            scores = comp.get("scores", {})
            for axis, value in scores.items():
                if value <= 2:
                    weakness_count[axis] = weakness_count.get(axis, 0) + 1
        gap = max(weakness_count, key=weakness_count.get) if weakness_count \
            else "ease_of_use"
        statement = (f"Stockei: gestao de estoque simples para pequenos "
                     f"negocios brasileiros, vencendo o mercado em '{gap}'.")
        self.insights.append({"type": "positioning", "gap_axis": gap,
                              "statement": statement,
                              "timestamp": datetime.now().isoformat()})
        logger.info("Positioning gap identified: %s", gap)
        return {"status": "completed", "gap_axis": gap,
                "positioning_statement": statement}
