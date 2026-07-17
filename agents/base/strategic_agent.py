"""
StrategicAgent Base Class
Base class for strategic agents (CEO, CFO, CTO)
Replicates pattern from agent_team_app/agents/agent_base.py
"""

from typing import Dict, List, Any, Optional
from agents.base.agent_base import AgentBase


class StrategicAgent(AgentBase):
    """Base class for strategic agents (CEO, CFO, CTO)"""

    category = "strategic"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, role=role, config=config)
        self.strategic_reviews: List[Dict[str, Any]] = []
