"""Tests for orchestration, teams, communication and learning."""

from orchestration.orchestrator import StockeiOrchestrator
from communication.message_broker import MessageBroker
from communication.event_system import EventSystem
from learning.continuous_learning import ContinuousLearning
from learning.feedback_system import FeedbackSystem
from agents.strategic.ceo_agent import CEOAgent
from agents.strategic.cfo_agent import CFOAgent
from teams.strategic_team import StrategicTeam
from main import build_system


def test_orchestrator_register_and_status():
    orch = StockeiOrchestrator()
    team = StrategicTeam(agents=[CEOAgent(), CFOAgent()])
    orch.register_team("strategic", team)
    status = orch.get_status()
    assert status["teams_count"] == 1
    assert "strategic" in status["teams"]


def test_full_system_builds():
    orch = build_system()
    status = orch.get_status()
    assert status["teams_count"] == 6
    total_agents = sum(t["agents_count"] for t in status["teams"].values())
    assert total_agents == 20


def test_workflow_execution():
    orch = build_system()
    result = orch.execute_workflow("kpi_review", {
        "team": "strategic",
        "steps": [{"agent": "CEO Agent",
                   "context": {"action": "monitor_kpis",
                               "metrics": {"arr": 5_000_000}}}],
    })
    assert result is not None
    assert orch.get_status()["workflows_executed"] == 1


def test_message_broker():
    broker = MessageBroker()
    ceo, cfo = CEOAgent(), CFOAgent()
    ceo.attach_communication(broker=broker)
    cfo.attach_communication(broker=broker)
    msg = ceo.send_message("CFO Agent", {"topic": "budget"})
    assert msg is not None
    assert len(broker.history) == 1


def test_event_system():
    events = EventSystem()
    seen = []
    events.subscribe("low_stock", lambda payload: seen.append(payload))
    events.publish("low_stock", {"sku": "ABC-1", "qty": 2})
    assert seen == [{"sku": "ABC-1", "qty": 2}]


def test_continuous_learning_cycle():
    cl = ContinuousLearning()
    ceo = CEOAgent()
    cl.register_agent(ceo)
    learnings = cl.collect_learnings()
    assert "CEO Agent" in str(learnings)


def test_feedback_system():
    fs = FeedbackSystem()
    ceo = CEOAgent()
    fs.submit_feedback(ceo, {"score": 9})
    assert len(ceo.feedback) == 1
