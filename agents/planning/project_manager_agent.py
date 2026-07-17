"""Project Manager Agent — delivery planning for Stockei."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base.planning_agent import PlanningAgent

logger = logging.getLogger(__name__)


class ProjectManagerAgent(PlanningAgent):
    """Project Manager agent: sprint planning, progress tracking and risks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Project Manager agent."""
        super().__init__(name="Project Manager Agent", role="Project Manager",
                         config=config or {})
        self.risks: List[Dict[str, Any]] = []

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the requested project management action."""
        action = context.get("action")
        if action == "plan_sprint":
            return self.plan_sprint(context.get("stories", []),
                                    context.get("capacity", 20))
        if action == "track_progress":
            return self.track_progress(context.get("sprint", {}))
        if action == "risk_register":
            return self.risk_register(context.get("risks", []))
        return {"status": "no_action"}

    def plan_sprint(self, stories: List[Dict[str, Any]],
                    capacity: int = 20) -> Dict[str, Any]:
        """Fill a sprint with stories up to the team's point capacity."""
        selected, deferred, used = [], [], 0
        for story in sorted(stories, key=lambda s: s.get("priority", 99)):
            points = story.get("points", 1)
            if used + points <= capacity:
                selected.append(story)
                used += points
            else:
                deferred.append(story)
        plan = {"capacity": capacity, "committed_points": used,
                "stories": selected, "deferred": deferred,
                "timestamp": datetime.now().isoformat()}
        self.plans.append({"type": "sprint_plan", "plan": plan})
        logger.info("PjM sprint planned: %d/%d points", used, capacity)
        return {"status": "completed", "sprint_plan": plan}

    def track_progress(self, sprint: Dict[str, Any]) -> Dict[str, Any]:
        """Compute completion percentage and on-track status."""
        total = sprint.get("committed_points", 0)
        done = sprint.get("done_points", 0)
        days_total = max(sprint.get("days_total", 10), 1)
        days_elapsed = sprint.get("days_elapsed", 0)
        pct_done = done / total if total else 0.0
        pct_time = days_elapsed / days_total
        on_track = pct_done >= pct_time - 0.1
        self.learning_history.append(
            {"timestamp": datetime.now().isoformat(),
             "action": "track_progress", "on_track": on_track})
        logger.info("PjM progress: %.0f%% done, on_track=%s",
                    pct_done * 100, on_track)
        return {"status": "completed", "pct_done": round(pct_done, 2),
                "pct_time": round(pct_time, 2), "on_track": on_track}

    def risk_register(self, risks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Score risks (probability * impact) and register the top ones."""
        register = []
        for risk in risks:
            score = risk.get("probability", 0.5) * risk.get("impact", 3)
            register.append({**risk, "score": round(score, 2),
                             "level": "high" if score >= 2 else
                             "medium" if score >= 1 else "low"})
        register.sort(key=lambda r: r["score"], reverse=True)
        self.risks = register
        logger.info("PjM risk register updated: %d risks", len(register))
        return {"status": "completed", "risk_register": register}
