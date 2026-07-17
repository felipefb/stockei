"""QA Agent — quality assurance for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.validation_agent import ValidationAgent

logger = logging.getLogger(__name__)


class QAAgent(ValidationAgent):
    """QA agent: runs test suites and produces regression reports."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the QA agent."""
        super().__init__(name="QA Agent", role="Quality Assurance Engineer",
                         config=config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested QA action."""
        action = context.get("action")
        if action == "run_test_suite":
            return self.run_test_suite(context.get("results", {}))
        if action == "regression_report":
            return self.regression_report(context.get("previous", {}),
                                          context.get("current", {}))
        return {"status": "no_action"}

    def run_test_suite(self, results: Dict[str, int]) -> Dict[str, Any]:
        """Summarize test suite results and decide pass/fail."""
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        total = passed + failed
        pass_rate = passed / total if total else 0.0
        verdict = "PASS" if failed == 0 and total > 0 else "FAIL"
        record = {"type": "test_suite", "total": total,
                  "pass_rate": round(pass_rate, 4), "verdict": verdict,
                  "timestamp": datetime.now().isoformat()}
        self.validations.append(record)
        logger.info("QA suite verdict: %s (%.0f%%)", verdict, pass_rate * 100)
        return {"status": "completed", "verdict": verdict,
                "pass_rate": round(pass_rate, 4), "failed": failed}

    def regression_report(self, previous: Dict[str, int],
                          current: Dict[str, int]) -> Dict[str, Any]:
        """Compare current run against a baseline to detect regressions."""
        prev_failed = previous.get("failed", 0)
        curr_failed = current.get("failed", 0)
        new_failures = max(0, curr_failed - prev_failed)
        regression = new_failures > 0
        report = {"previous_failed": prev_failed, "current_failed": curr_failed,
                  "new_failures": new_failures, "regression": regression}
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "regression_report", "report": report})
        logger.info("QA regression detected: %s", regression)
        return {"status": "completed", **report}
