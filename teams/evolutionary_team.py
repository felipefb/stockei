"""
EvolutionaryTeam
Evolutionary Team for Stockei, grouping the evolutionary category agents.
"""

from typing import Any, List, Optional

from teams.team_base import TeamBase


class EvolutionaryTeam(TeamBase):
    """Evolutionary Team (default name: "Evolutionary Team")."""

    def __init__(self, name: str = "Evolutionary Team",
                 agents: Optional[List[Any]] = None) -> None:
        """
        Initialize the evolutionary team.

        Args:
            name: Team name (defaults to "Evolutionary Team").
            agents: Initial list of agents.
        """
        super().__init__(name=name, agents=agents)
