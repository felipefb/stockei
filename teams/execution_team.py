"""
ExecutionTeam
Execution Team for Stockei, grouping the execution category agents.
"""

from typing import Any, List, Optional

from teams.team_base import TeamBase


class ExecutionTeam(TeamBase):
    """Execution Team (default name: "Execution Team")."""

    def __init__(self, name: str = "Execution Team",
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the execution team.

        Args:
            name: Team name (defaults to "Execution Team").
            agents: Initial list of agents.
        """
        super().__init__(name=name, agents=agents)
