from __future__ import annotations

# Simple hooks for future visual components.


class RedView:
    def __init__(self, world_snapshot_provider):
        self._snapshot = world_snapshot_provider

    def get_summary(self) -> str:
        snapshot = self._snapshot()
        hypo = snapshot.get("hypotheses", {})
        return f"Red posture hypotheses: {len(hypo)} entries"
