"""Customer Success Agent — retention and adoption for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.commercialization_agent import CommercializationAgent

logger = logging.getLogger(__name__)


class CustomerSuccessAgent(CommercializationAgent):
    """Customer Success agent: onboarding, churn risk analysis and NPS."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Customer Success agent."""
        super().__init__(name="Customer Success Agent",
                         role="Customer Success Manager", config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested customer success action."""
        action = context.get("action")
        if action == "onboard_customer":
            return self.onboard_customer(context.get("customer", {}))
        if action == "churn_risk_analysis":
            return self.churn_risk_analysis(context.get("usage", {}))
        if action == "nps_report":
            return self.nps_report(context.get("scores", []))
        return {"status": "no_action"}

    def onboard_customer(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Create an onboarding checklist for a new Stockei customer."""
        checklist = ["Importar catalogo de produtos",
                     "Registrar estoque inicial",
                     "Configurar alertas de estoque baixo",
                     "Convidar equipe", "Primeira movimentacao registrada"]
        record = {"customer": customer.get("name", "unknown"),
                  "plan": customer.get("plan", "Starter"),
                  "checklist": checklist, "progress": 0,
                  "timestamp": datetime.now().isoformat()}
        self.activities.append({"type": "onboarding", **record})
        logger.info("CS onboarding started for '%s'", record["customer"])
        return {"status": "completed", "onboarding": record}

    def churn_risk_analysis(self, usage: Dict[str, Any]) -> Dict[str, Any]:
        """Score churn risk from product usage signals."""
        risk = 0
        if usage.get("days_since_last_login", 0) > 14:
            risk += 40
        if usage.get("weekly_movements", 0) < 3:
            risk += 30
        if not usage.get("alerts_configured", True):
            risk += 20
        if usage.get("support_tickets_open", 0) > 2:
            risk += 10
        level = "high" if risk >= 60 else "medium" if risk >= 30 else "low"
        actions = (["Ligar para o cliente", "Oferecer sessao de treinamento"]
                   if level == "high" else ["Enviar email de engajamento"]
                   if level == "medium" else [])
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "churn_risk_analysis", "risk": risk})
        logger.info("CS churn risk: %d (%s)", risk, level)
        return {"status": "completed", "risk_score": risk,
                "risk_level": level, "actions": actions}

    def nps_report(self, scores: List[int]) -> Dict[str, Any]:
        """Compute NPS from a list of 0-10 survey scores."""
        if not scores:
            return {"status": "completed", "nps": None, "note": "no responses"}
        promoters = sum(1 for s in scores if s >= 9)
        detractors = sum(1 for s in scores if s <= 6)
        nps = round(100 * (promoters - detractors) / len(scores))
        self.activities.append({"type": "nps_report", "nps": nps,
                                "responses": len(scores),
                                "timestamp": datetime.now().isoformat()})
        logger.info("CS NPS: %d (%d responses)", nps, len(scores))
        return {"status": "completed", "nps": nps, "promoters": promoters,
                "detractors": detractors, "responses": len(scores)}
