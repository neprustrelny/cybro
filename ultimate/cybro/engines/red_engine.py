from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class Intent:
    """Intent describes WHY an action should happen."""

    goal: str
    noise_budget: float
    time_horizon: int
    exposure_risk: float
    stealth_score: float = 0.5
    value_score: float = 0.5

    def evaluate_success(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Assess stealth and strategic returns."""
        success = outcome.get("success", True)
        stealth_penalty = outcome.get("noise", 0.0)
        self.stealth_score = max(0.0, min(1.0, self.stealth_score - stealth_penalty))
        self.value_score = (
            (self.value_score * 0.6) + (1.0 if success else 0.2) * 0.4
        )
        return {
            "stealth_score": round(self.stealth_score, 3),
            "value_score": round(self.value_score, 3),
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RedEngine:
    """Intent-based red team reasoning."""

    def __init__(self) -> None:
        self.default_time_horizon = 60  # seconds

    def build_intent(
        self, world_model, label: str, context: Dict[str, Any]
    ) -> Intent:
        dominant = world_model.get_dominant_hypothesis()
        exposure = 0.4
        if dominant and "defender_active" in (dominant.evidence or {}):
            exposure = 0.7
        goal = context.get("goal", label)
        noise_budget = 0.2 if context.get("stealth") else 0.5
        return Intent(
            goal=goal,
            noise_budget=noise_budget,
            time_horizon=context.get("time_horizon", self.default_time_horizon),
            exposure_risk=exposure,
        )
