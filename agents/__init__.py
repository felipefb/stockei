"""Stockei agents package.

Exposes every concrete agent class and the ALL_AGENTS registry mapping
agent name -> class.
"""

from typing import Dict, Type

from agents.base.agent_base import AgentBase
from agents.strategic import CEOAgent, CFOAgent, CTOAgent
from agents.planning import (ProductManagerAgent, TechArchitectAgent,
                             ProjectManagerAgent)
from agents.execution import (BackendEngineerAgent, FrontendEngineerAgent,
                              MLAIEngineerAgent, DevOpsAgent)
from agents.validation import QAAgent, SecurityAgent, ComplianceAgent
from agents.commercialization import (SalesAgent, MarketingAgent,
                                      CustomerSuccessAgent, DesignUXAgent)
from agents.evolutionary import (ProductEvolutionAgent, MarketResearchAgent,
                                 CompetitiveAnalysisAgent)

ALL_AGENTS: Dict[str, Type[AgentBase]] = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "cto": CTOAgent,
    "product_manager": ProductManagerAgent,
    "tech_architect": TechArchitectAgent,
    "project_manager": ProjectManagerAgent,
    "backend_engineer": BackendEngineerAgent,
    "frontend_engineer": FrontendEngineerAgent,
    "ml_ai_engineer": MLAIEngineerAgent,
    "devops": DevOpsAgent,
    "qa": QAAgent,
    "security": SecurityAgent,
    "compliance": ComplianceAgent,
    "sales": SalesAgent,
    "marketing": MarketingAgent,
    "customer_success": CustomerSuccessAgent,
    "design_ux": DesignUXAgent,
    "product_evolution": ProductEvolutionAgent,
    "market_research": MarketResearchAgent,
    "competitive_analysis": CompetitiveAnalysisAgent,
}

__all__ = ["ALL_AGENTS"] + [cls.__name__ for cls in ALL_AGENTS.values()]
