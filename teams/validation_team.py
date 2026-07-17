"""
ValidationTeam
Validation Team for Stockei, grouping the validation category agents.
"""

from typing import Any, List, Optional

from teams.team_base import TeamBase


class ValidationTeam(TeamBase):
    """Validation Team (default name: "Validation Team")."""

    def __init__(self, name: str = "Validation Team",
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the validation team.

        Args:
            name: Team name (defaults to "Validation Team").
            agents: Initial list of agents.
        """
        super().__init__(name=name, agents=agents)
