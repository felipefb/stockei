"""
CommercializationAgent Base Class
Base class for commercialization agents (Sales, Marketing, Customer Success, Design/UX)
Replicates pattern from agent_team_app/agents/agent_base.py
"""

from typing import Dict, List, Any, Optional
from agents.base.agent_base import AgentBase


class CommercializationAgent(AgentBase):
    """Base class for commercialization agents (Sales, Marketing, Customer Success, Design/UX)"""

    category = "commercialization"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, role=role, config=config)
        self.activities: List[Dict[str, Any]] = []
