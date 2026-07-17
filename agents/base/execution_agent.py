"""
ExecutionAgent Base Class
Base class for execution agents (Backend, Frontend, ML/AI, DevOps)
Replicates pattern from agent_team_app/agents/agent_base.py
"""

from typing import Dict, List, Any, Optional
from agents.base.agent_base import AgentBase


class ExecutionAgent(AgentBase):
    """Base class for execution agents (Backend, Frontend, ML/AI, DevOps)"""

    category = "execution"

    def __init__(self, name: str, role: str,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, role=role, config=config)
        self.tasks: List[Dict[str, Any]] = []
