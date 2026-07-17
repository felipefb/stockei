"""
StrategicTeam
Strategic Team for Stockei, grouping the strategic category agents.
"""

from typing import Any, List, Optional

from teams.team_base import TeamBase


class StrategicTeam(TeamBase):
    """Strategic Team (default name: "Strategic Team")."""

    def __init__(self, name: str = "Strategic Team",
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the strategic team.

        Args:
            name: Team name (defaults to "Strategic Team").
            agents: Initial list of agents.
        """
        super().__init__(name=name, agents=agents)
