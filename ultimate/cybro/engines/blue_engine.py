from __future__ import annotations

import random
import time
from typing import Dict, Any


class BlueEngine:
    """Defensive posture logic."""

    VALID_POSTURES = ("passive", "deceptive", "aggressive")

    def __init__(self) -> None:
        self.posture = "passive"
        self.last_switch = time.time()

    def evaluate_posture(self, world_model, intent) -> str:
        dominant = world_model.get_dominant_hypothesis()
        if dominant and dominant.confidence > 0.8:
            self.posture = "aggressive"
        elif intent.exposure_risk > 0.6:
            self.posture = "deceptive"
        else:
            # Small chance to randomly probe with deception.
            self.posture = random.choice(["passive", "deceptive"])
        self.last_switch = time.time()
        return self.posture

    def set_posture(self, posture: str) -> None:
        if posture not in self.VALID_POSTURES:
            raise ValueError("Invalid posture")
        self.posture = posture

    def delay_response(self, context: Dict[str, Any]) -> None:
        """Blue team can intentionally delay to gather intel."""
        delay = context.get("delay_seconds", 2)
        time.sleep(min(delay, 5))
