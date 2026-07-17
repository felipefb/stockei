"""DevOps Agent — deployment and reliability for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agents.base.execution_agent import ExecutionAgent

logger = logging.getLogger(__name__)


class DevOpsAgent(ExecutionAgent):
    """DevOps agent: deployments, health monitoring and incident response."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the DevOps agent."""
        super().__init__(name="DevOps Agent", role="DevOps Engineer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested operations action."""
        action = context.get("action")
        if action == "deploy":
            return self.deploy(context.get("version", "0.0.0"),
                               context.get("environment", "staging"),
                               context.get("checks", {}))
        if action == "monitor_health":
            return self.monitor_health(context.get("metrics", {}))
        if action == "incident_response":
            return self.incident_response(context.get("alert", {}))
        return {"status": "no_action"}

    def deploy(self, version: str, environment: str,
               checks: Dict[str, bool]) -> Dict[str, Any]:
        """Deploy a version if pre-deploy checks pass."""
        required = ["tests_passed", "migrations_reviewed"]
        failed = [c for c in required if not checks.get(c, False)]
        deployed = not failed
        record = {"type": "deploy", "version": version,
                  "environment": environment, "deployed": deployed,
                  "timestamp": datetime.now().isoformat()}
        self.tasks.append(record)
        logger.info("DevOps deploy %s to %s: %s", version, environment,
                    "OK" if deployed else "BLOCKED")
        return {"status": "completed", "deployed": deployed,
                "blocked_by": failed}

    def monitor_health(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate service health from error rate, latency and CPU."""
        alerts = []
        if metrics.get("error_rate", 0) > 0.01:
            alerts.append("Error rate above 1%")
        if metrics.get("p95_latency_ms", 0) > 500:
            alerts.append("p95 latency above 500ms")
        if metrics.get("cpu_pct", 0) > 85:
            alerts.append("CPU above 85%")
        healthy = not alerts
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "monitor_health", "healthy": healthy})
        logger.info("DevOps health: healthy=%s", healthy)
        return {"status": "completed", "healthy": healthy, "alerts": alerts}

    def incident_response(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a response plan based on alert severity."""
        severity = alert.get("severity", "low")
        steps = ["Acknowledge alert", "Check dashboards"]
        if severity in ("high", "critical"):
            steps += ["Page on-call engineer", "Consider rollback",
                      "Open incident channel"]
        else:
            steps += ["Create ticket for next sprint"]
        self.tasks.append({"type": "incident_response", "alert": alert,
                           "steps": steps,
                           "timestamp": datetime.now().isoformat()})
        logger.info("DevOps incident response (%s)", severity)
        return {"status": "completed", "severity": severity, "steps": steps}
