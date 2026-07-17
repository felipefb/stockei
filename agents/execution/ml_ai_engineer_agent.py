"""ML/AI Engineer Agent — demand forecasting and inventory intelligence."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.execution_agent import ExecutionAgent

logger = logging.getLogger(__name__)


class MLAIEngineerAgent(ExecutionAgent):
    """ML/AI Engineer agent: moving-average demand forecast, reorder point
    calculation and simple anomaly detection on stock movements."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the ML/AI Engineer agent."""
        super().__init__(name="ML/AI Engineer Agent", role="ML/AI Engineer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested ML action."""
        action = context.get("action")
        if action == "demand_forecast":
            return self.demand_forecast(context.get("history", []),
                                        context.get("window", 3),
                                        context.get("periods", 3))
        if action == "reorder_point":
            return self.reorder_point(context.get("history", []),
                                      context.get("lead_time_days", 7),
                                      context.get("safety_stock", 0))
        if action == "anomaly_detection":
            return self.anomaly_detection(context.get("series", []),
                                          context.get("threshold", 2.0))
        return {"status": "no_action"}

    def demand_forecast(self, history: List[float], window: int = 3,
                        periods: int = 3) -> Dict[str, Any]:
        """Forecast future demand using a simple moving average."""
        if not history:
            return {"status": "completed", "forecast": [],
                    "note": "no history provided"}
        series = list(history)
        forecast = []
        for _ in range(periods):
            avg = sum(series[-window:]) / min(window, len(series))
            forecast.append(round(avg, 2))
            series.append(avg)
        self.tasks.append({"type": "demand_forecast",
                           "timestamp": datetime.now().isoformat(),
                           "forecast": forecast})
        logger.info("ML demand forecast: %s", forecast)
        return {"status": "completed", "forecast": forecast,
                "method": "moving_average", "window": window}

    def reorder_point(self, history: List[float], lead_time_days: int = 7,
                      safety_stock: float = 0) -> Dict[str, Any]:
        """Compute reorder point = avg daily demand * lead time + safety stock."""
        avg_daily = (sum(history) / len(history)) if history else 0.0
        rop = avg_daily * lead_time_days + safety_stock
        result = {"status": "completed",
                  "avg_daily_demand": round(avg_daily, 2),
                  "lead_time_days": lead_time_days,
                  "safety_stock": safety_stock,
                  "reorder_point": round(rop, 2)}
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "reorder_point", "result": result})
        logger.info("ML reorder point: %.2f", rop)
        return result

    def anomaly_detection(self, series: List[float],
                          threshold: float = 2.0) -> Dict[str, Any]:
        """Flag points more than `threshold` standard deviations from mean."""
        if len(series) < 2:
            return {"status": "completed", "anomalies": [],
                    "note": "insufficient data"}
        mean = sum(series) / len(series)
        variance = sum((x - mean) ** 2 for x in series) / len(series)
        std = variance ** 0.5
        anomalies = []
        if std > 0:
            anomalies = [{"index": i, "value": v,
                          "z_score": round((v - mean) / std, 2)}
                         for i, v in enumerate(series)
                         if abs((v - mean) / std) > threshold]
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "anomaly_detection", "count": len(anomalies)})
        logger.info("ML anomalies detected: %d", len(anomalies))
        return {"status": "completed", "mean": round(mean, 2),
                "std": round(std, 2), "anomalies": anomalies}
