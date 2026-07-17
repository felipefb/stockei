"""Tests for Stockei agents."""

from agents import ALL_AGENTS
from agents.strategic.ceo_agent import CEOAgent


def test_all_agents_instantiate():
    agents = [cls() for cls in ALL_AGENTS.values()]
    assert len(agents) == 20


def test_all_agents_have_status():
    for cls in ALL_AGENTS.values():
        status = cls().get_status()
        assert {"name", "role", "category"} <= set(status)


def test_unknown_action_returns_no_action():
    for cls in ALL_AGENTS.values():
        result = cls().execute({"action": "__does_not_exist__"})
        assert result.get("status") == "no_action"


def test_ceo_monitor_kpis_good():
    ceo = CEOAgent()
    result = ceo.execute({"action": "monitor_kpis", "metrics": {
        "arr": 5_500_000, "churn_rate": 0.04, "cac": 450,
        "ltv": 12_000, "market_share": 0.18,
    }})
    assert result["health_status"] in {"EXCELLENT", "GOOD"}
    assert len(ceo.learning_history) >= 1


def test_ceo_monitor_kpis_critical():
    ceo = CEOAgent()
    result = ceo.execute({"action": "monitor_kpis", "metrics": {
        "arr": 2_000_000, "churn_rate": 0.15, "cac": 900,
        "ltv": 5_000, "market_share": 0.05,
    }})
    assert result["health_status"] == "CRITICAL"
    assert "Increase Customer Success focus" in result["actions"]


def test_learning_from_feedback():
    ceo = CEOAgent()
    ceo.learn_from_feedback({"score": 8, "comment": "boa decisão"})
    assert len(ceo.feedback) == 1
    assert ceo.feedback[0]["processed"] is True
