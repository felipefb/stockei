"""
PlanningAgent Base Class
Base class for planning agents (Product Manager, Tech Architect, Project Manager)
Replicates pattern from agent_team_app/agents/agent_base.py
"""

from typing import Dict, List, Any, Optional
from agents.base.agent_base import AgentBase


class PlanningAgent(AgentBase):
    """Base class for planning agents (Product Manager, Tech Architect, Project Manager)"""

    category = "planning"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, role=role, config=config)
        self.plans: List[Dict[str, Any]] = []
