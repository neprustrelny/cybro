from __future__ import annotations


class BlueView:
    def __init__(self, world_snapshot_provider):
        self._snapshot = world_snapshot_provider

    def get_summary(self) -> str:
        snapshot = self._snapshot()
        history = snapshot.get("history_size", 0)
        return f"Blue posture history size: {history}"
