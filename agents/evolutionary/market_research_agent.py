"""Market Research Agent — Brazilian inventory-management market research."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.evolutionary_agent import EvolutionaryAgent

logger = logging.getLogger(__name__)


class MarketResearchAgent(EvolutionaryAgent):
    """Market Research agent: market scans and TAM/SAM/SOM estimation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Market Research agent."""
        super().__init__(name="Market Research Agent",
                         role="Market Research Analyst", config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested research action."""
        action = context.get("action")
        if action == "market_scan":
            return self.market_scan(context.get("trends", []))
        if action == "tam_sam_som":
            return self.tam_sam_som(context.get("assumptions", {}))
        return {"status": "no_action"}

    def market_scan(self, trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify market trends as opportunity or threat by momentum."""
        classified = []
        for trend in trends:
            momentum = trend.get("momentum", 0)
            classified.append({**trend,
                               "classification": "opportunity"
                               if momentum > 0 else "threat"})
        if not classified:
            classified = [
                {"trend": "Digitalizacao de PMEs no varejo brasileiro",
                 "momentum": 1, "classification": "opportunity"},
                {"trend": "ERPs incumbentes adicionando modulos de estoque",
                 "momentum": -1, "classification": "threat"},
            ]
        self.insights.append({"type": "market_scan", "trends": classified,
                              "timestamp": datetime.now().isoformat()})
        logger.info("Market scan: %d trends", len(classified))
        return {"status": "completed", "trends": classified}

    def tam_sam_som(self, assumptions: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate TAM/SAM/SOM for Brazilian inventory-management SaaS.

        Defaults: ~6.4M small businesses with inventory in Brazil, average
        ticket R$ 100/month, 30% digitally addressable, 2% obtainable share.
        """
        businesses = assumptions.get("target_businesses", 6_400_000)
        avg_ticket_monthly_brl = assumptions.get("avg_ticket_brl", 100.0)
        addressable_pct = assumptions.get("addressable_pct", 0.30)
        obtainable_pct = assumptions.get("obtainable_pct", 0.02)

        tam = businesses * avg_ticket_monthly_brl * 12
        sam = tam * addressable_pct
        som = sam * obtainable_pct
        result = {"status": "completed",
                  "tam_brl_year": round(tam, 2),
                  "sam_brl_year": round(sam, 2),
                  "som_brl_year": round(som, 2),
                  "assumptions": {"target_businesses": businesses,
                                  "avg_ticket_brl": avg_ticket_monthly_brl,
                                  "addressable_pct": addressable_pct,
                                  "obtainable_pct": obtainable_pct}}
        self.insights.append({"type": "tam_sam_som", "result": result,
                              "timestamp": datetime.now().isoformat()})
        logger.info("TAM/SAM/SOM computed: SOM R$%.0f/year", som)
        return result
