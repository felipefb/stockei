"""Compliance Agent — LGPD and audit compliance for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.validation_agent import ValidationAgent

logger = logging.getLogger(__name__)


class ComplianceAgent(ValidationAgent):
    """Compliance agent: Brazilian LGPD checks and audit trail validation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Compliance agent."""
        super().__init__(name="Compliance Agent", role="Compliance Officer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested compliance action."""
        action = context.get("action")
        if action == "lgpd_check":
            return self.lgpd_check(context.get("practices", {}))
        if action == "audit_trail":
            return self.audit_trail(context.get("events", []))
        return {"status": "no_action"}

    def lgpd_check(self, practices: Dict[str, bool]) -> Dict[str, Any]:
        """Check LGPD (Lei Geral de Protecao de Dados) requirements."""
        requirements = {
            "consent_management": "Base legal / consentimento registrado",
            "data_minimization": "Coleta apenas dados necessarios",
            "right_to_deletion": "Exclusao de dados sob solicitacao",
            "data_portability": "Exportacao de dados do titular",
            "dpo_assigned": "Encarregado (DPO) designado",
            "breach_notification": "Processo de notificacao a ANPD",
        }
        gaps = [{"requirement": key, "description": desc}
                for key, desc in requirements.items()
                if not practices.get(key, False)]
        compliant = not gaps
        record = {"type": "lgpd_check", "compliant": compliant,
                  "gaps": len(gaps), "timestamp": datetime.now().isoformat()}
        self.validations.append(record)
        logger.info("LGPD check: compliant=%s (%d gaps)", compliant, len(gaps))
        return {"status": "completed", "compliant": compliant, "gaps": gaps}

    def audit_trail(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that audit events contain required fields."""
        required = {"user_id", "action", "timestamp"}
        invalid = [{"index": i, "missing": sorted(required - set(e))}
                   for i, e in enumerate(events)
                   if not required.issubset(e)]
        valid = not invalid
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "audit_trail", "valid": valid,
             "events_checked": len(events)})
        logger.info("Audit trail check: valid=%s", valid)
        return {"status": "completed", "valid": valid,
                "events_checked": len(events), "invalid_events": invalid}
