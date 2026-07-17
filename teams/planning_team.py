"""
PlanningTeam
Planning Team for Stockei, grouping the planning category agents.
"""

from typing import Any, List, Optional

from teams.team_base import TeamBase


class PlanningTeam(TeamBase):
    """Planning Team (default name: "Planning Team")."""

    def __init__(self, name: str = "Planning Team",
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the planning team.

        Args:
            name: Team name (defaults to "Planning Team").
            agents: Initial list of agents.
        """
        super().__init__(name=name, agents=agents)
