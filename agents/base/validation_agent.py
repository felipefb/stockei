"""
ValidationAgent Base Class
Base class for validation agents (QA, Security, Compliance)
Replicates pattern from agent_team_app/agents/agent_base.py
"""

from typing import Dict, List, Any, Optional
from agents.base.agent_base import AgentBase


class ValidationAgent(AgentBase):
    """Base class for validation agents (QA, Security, Compliance)"""

    category = "validation"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, role=role, config=config)
        self.validations: List[Dict[str, Any]] = []
