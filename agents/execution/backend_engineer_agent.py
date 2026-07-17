"""Backend Engineer Agent — API implementation for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.execution_agent import ExecutionAgent

logger = logging.getLogger(__name__)


class BackendEngineerAgent(ExecutionAgent):
    """Backend Engineer agent: implements and reviews inventory APIs
    (produtos, movimentacoes, alertas de estoque baixo)."""

    KNOWN_ENDPOINTS: List[str] = [
        "/api/produtos", "/api/movimentacoes", "/api/alertas/estoque-baixo",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Backend Engineer agent."""
        super().__init__(name="Backend Engineer Agent",
                         role="Backend Engineer", config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested backend action."""
        action = context.get("action")
        if action == "implement_api":
            return self.implement_api(context.get("endpoint", ""),
                                      context.get("methods", ["GET"]))
        if action == "review_code":
            return self.review_code(context.get("code_meta", {}))
        return {"status": "no_action"}

    def implement_api(self, endpoint: str,
                      methods: List[str]) -> Dict[str, Any]:
        """Plan the implementation of an inventory API endpoint."""
        known = endpoint in self.KNOWN_ENDPOINTS
        spec = {
            "endpoint": endpoint,
            "methods": methods,
            "auth_required": True,
            "validations": ["tenant_id", "payload_schema"],
            "known_domain_endpoint": known,
            "tests": [f"test_{m.lower()}_{endpoint.strip('/').replace('/', '_')}"
                      for m in methods],
        }
        self.tasks.append({"type": "implement_api", "spec": spec,
                           "timestamp": datetime.now().isoformat(),
                           "status": "planned"})
        logger.info("Backend planned API %s %s", methods, endpoint)
        return {"status": "completed", "implementation": spec}

    def review_code(self, code_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Review code metadata for common backend quality issues."""
        issues = []
        if not code_meta.get("has_tests", False):
            issues.append("Missing unit tests")
        if code_meta.get("function_length", 0) > 50:
            issues.append("Function too long (>50 lines)")
        if not code_meta.get("input_validation", True):
            issues.append("Missing input validation")
        if code_meta.get("raw_sql", False):
            issues.append("Raw SQL detected — use parameterized queries")
        approved = not issues
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "review_code", "approved": approved})
        logger.info("Backend code review: approved=%s", approved)
        return {"status": "completed", "approved": approved, "issues": issues}
