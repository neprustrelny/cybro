from __future__ import annotations

from typing import Dict, Any


class OfflineModelRegistry:
    """Keeps lightweight references to offline AI models."""

    def __init__(self) -> None:
        self.models: Dict[str, Any] = {}

    def register(self, name: str, model: Any) -> None:
        self.models[name] = model

    def get(self, name: str) -> Any:
        return self.models.get(name)
