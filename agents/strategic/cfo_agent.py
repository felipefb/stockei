"""CFO Agent — financial oversight for Stockei (inventory SaaS)."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agents.base.strategic_agent import StrategicAgent

logger = logging.getLogger(__name__)


class CFOAgent(StrategicAgent):
    """Chief Financial Officer agent: budget reviews, cash flow forecasts
    and pricing analysis for the Stockei plans (in BRL)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the CFO agent with Stockei plan pricing in R$."""
        super().__init__(name="CFO Agent", role="Chief Financial Officer",
                         config=config or {})
        self.plan_prices_brl: Dict[str, float] = {
            "Starter": 49.90,
            "Pro": 99.90,
            "Business": 199.90,
        }

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested financial action."""
        action = context.get("action")
        if action == "budget_review":
            return self.budget_review(context.get("budget", {}),
                                      context.get("actuals", {}))
        if action == "cash_flow_forecast":
            return self.cash_flow_forecast(
                context.get("cash_balance", 0.0),
                context.get("monthly_revenue", 0.0),
                context.get("monthly_expenses", 0.0),
                context.get("months", 6))
        if action == "pricing_analysis":
            return self.pricing_analysis(context.get("subscribers", {}))
        return {"status": "no_action"}

    def budget_review(self, budget: Dict[str, float],
                      actuals: Dict[str, float]) -> Dict[str, Any]:
        """Compare actual spend against budget per cost center."""
        review = {}
        for center, planned in budget.items():
            actual = actuals.get(center, 0.0)
            variance = (actual - planned) / planned if planned else 0.0
            review[center] = {
                "budget": planned,
                "actual": actual,
                "variance": round(variance, 4),
                "over_budget": variance > 0.05,
            }
        result = {"status": "completed", "review": review,
                  "flags": [c for c, r in review.items() if r["over_budget"]]}
        self.strategic_reviews.append(
            {"timestamp": datetime.now().isoformat(),
             "type": "budget_review", "result": result})
        logger.info("CFO budget review: %d cost centers", len(review))
        return result

    def cash_flow_forecast(self, cash_balance: float, monthly_revenue: float,
                           monthly_expenses: float,
                           months: int = 6) -> Dict[str, Any]:
        """Project cash balance forward and compute runway in months."""
        burn = monthly_expenses - monthly_revenue
        projection = []
        balance = cash_balance
        for month in range(1, months + 1):
            balance += monthly_revenue - monthly_expenses
            projection.append({"month": month, "balance": round(balance, 2)})
        runway = None if burn <= 0 else round(cash_balance / burn, 1)
        result = {"status": "completed", "projection": projection,
                  "monthly_burn": round(burn, 2), "runway_months": runway}
        self.record_decision({"type": "cash_flow_forecast",
                              "runway_months": runway})
        logger.info("CFO cash flow forecast: runway=%s months", runway)
        return result

    def pricing_analysis(self, subscribers: Dict[str, int]) -> Dict[str, Any]:
        """Compute MRR/ARR per plan (Starter/Pro/Business, values in R$)."""
        breakdown = {}
        total_mrr = 0.0
        for plan, price in self.plan_prices_brl.items():
            count = subscribers.get(plan, 0)
            mrr = count * price
            total_mrr += mrr
            breakdown[plan] = {"price_brl": price, "subscribers": count,
                               "mrr_brl": round(mrr, 2)}
        result = {"status": "completed", "plans": breakdown,
                  "total_mrr_brl": round(total_mrr, 2),
                  "total_arr_brl": round(total_mrr * 12, 2)}
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "pricing_analysis", "result": result})
        logger.info("CFO pricing analysis: MRR R$%.2f", total_mrr)
        return result
