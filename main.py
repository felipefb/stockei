"""
Stockei - Main Entry Point
Initialize and run the agent system.
"""

import logging
from datetime import datetime

from orchestration.orchestrator import StockeiOrchestrator
from communication.message_broker import MessageBroker
from communication.event_system import EventSystem
from learning.continuous_learning import ContinuousLearning
from teams.strategic_team import StrategicTeam
from teams.planning_team import PlanningTeam
from teams.execution_team import ExecutionTeam
from teams.validation_team import ValidationTeam
from teams.commercialization_team import CommercializationTeam
from teams.evolutionary_team import EvolutionaryTeam
from agents import ALL_AGENTS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEAM_CLASSES = {
    "strategic": StrategicTeam,
    "planning": PlanningTeam,
    "execution": ExecutionTeam,
    "validation": ValidationTeam,
    "commercialization": CommercializationTeam,
    "evolutionary": EvolutionaryTeam,
}


def build_system() -> StockeiOrchestrator:
    """Instantiate all agents, group them into teams, wire communication."""
    orchestrator = StockeiOrchestrator()
    broker = MessageBroker()
    events = EventSystem()
    learning = ContinuousLearning()

    # Instantiate agents grouped by category
    agents_by_category = {}
    for cls in ALL_AGENTS.values():
        agent = cls()
        agents_by_category.setdefault(agent.category, []).append(agent)
        learning.register_agent(agent)

    # Build and register teams
    for category, team_cls in TEAM_CLASSES.items():
        team = team_cls(agents=agents_by_category.get(category, []))
        orchestrator.register_team(category, team)

    orchestrator.register_agent_communication(broker, events)
    orchestrator.learning = learning
    orchestrator.broker = broker
    orchestrator.events = events
    return orchestrator


def main():
    """Main entry point."""
    print("=" * 80)
    print("STOCKEI - SISTEMA DE AGENTES ESPECIALIZADOS")
    print("=" * 80)
    print(f"Iniciado em: {datetime.now().isoformat()}")
    print()

    orchestrator = build_system()

    # Demo: CEO monitors KPIs
    ceo = orchestrator.teams["strategic"].agents["CEO Agent"]
    print("Testando CEO Agent...")
    metrics = {
        "arr": 5_500_000,
        "churn_rate": 0.04,
        "cac": 450,
        "ltv": 12_000,
        "market_share": 0.18,
    }
    result = ceo.execute({"action": "monitor_kpis", "metrics": metrics})
    print(f"CEO Report: {result.get('health_status')}")
    print()

    # Demo: workflow via orchestrator
    orchestrator.execute_workflow(
        "kpi_review",
        {"team": "strategic",
         "steps": [{"agent": ceo.name,
                    "context": {"action": "monitor_kpis", "metrics": metrics}}]},
    )

    print(f"Orchestrator Status: {orchestrator.get_status()}")
    print(f"CEO Status: {ceo.get_status()}")
    print()
    print("=" * 80)
    print("Sistema de Agentes Stockei Ativo!")
    print("=" * 80)


if __name__ == "__main__":
    main()
