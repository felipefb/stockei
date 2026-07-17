"""
EvolutionaryAgent Base Class
Base class for evolutionary agents (Product Evolution, Market Research, Competitive Analysis)
Replicates pattern from agent_team_app/agents/agent_base.py
"""

from typing import Dict, List, Any, Optional
from agents.base.agent_base import AgentBase


class EvolutionaryAgent(AgentBase):
    """Base class for evolutionary agents (Product Evolution, Market Research, Competitive Analysis)"""

    category = "evolutionary"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, role=role, config=config)
        self.insights: List[Dict[str, Any]] = []
