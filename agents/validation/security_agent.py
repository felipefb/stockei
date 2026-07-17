"""Security Agent — application security for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.validation_agent import ValidationAgent

logger = logging.getLogger(__name__)


class SecurityAgent(ValidationAgent):
    """Security agent: audits security posture and triages vulnerabilities."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Security agent."""
        super().__init__(name="Security Agent", role="Security Engineer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested security action."""
        action = context.get("action")
        if action == "security_audit":
            return self.security_audit(context.get("posture", {}))
        if action == "vulnerability_scan":
            return self.vulnerability_scan(context.get("findings", []))
        return {"status": "no_action"}

    def security_audit(self, posture: Dict[str, bool]) -> Dict[str, Any]:
        """Audit basic security controls and score the posture."""
        controls = ["https_everywhere", "password_hashing", "rate_limiting",
                    "mfa_available", "encrypted_backups", "least_privilege"]
        missing = [c for c in controls if not posture.get(c, False)]
        score = round(100 * (len(controls) - len(missing)) / len(controls))
        record = {"type": "security_audit", "score": score, "missing": missing,
                  "timestamp": datetime.now().isoformat()}
        self.validations.append(record)
        logger.info("Security audit score: %d", score)
        return {"status": "completed", "score": score,
                "missing_controls": missing}

    def vulnerability_scan(self,
                           findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Triage vulnerability findings by severity with SLA in days."""
        sla = {"critical": 1, "high": 7, "medium": 30, "low": 90}
        triaged = []
        for f in findings:
            severity = f.get("severity", "low").lower()
            triaged.append({**f, "fix_sla_days": sla.get(severity, 90)})
        triaged.sort(key=lambda f: f["fix_sla_days"])
        blocking = [f for f in triaged if f["fix_sla_days"] <= 7]
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "vulnerability_scan", "count": len(triaged)})
        logger.info("Security scan: %d findings, %d blocking",
                    len(triaged), len(blocking))
        return {"status": "completed", "findings": triaged,
                "release_blocking": blocking}
