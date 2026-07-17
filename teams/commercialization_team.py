"""
CommercializationTeam
Commercialization Team for Stockei, grouping the commercialization category agents.
"""

from typing import Any, List, Optional

from teams.team_base import TeamBase


class CommercializationTeam(TeamBase):
    """Commercialization Team (default name: "Commercialization Team")."""

    def __init__(self, name: str = "Commercialization Team",
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the commercialization team.

        Args:
            name: Team name (defaults to "Commercialization Team").
            agents: Initial list of agents.
        """
        super().__init__(name=name, agents=agents)
