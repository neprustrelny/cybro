from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class Hypothesis:
    """Represents a competing interpretation of the environment."""

    name: str
    confidence: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    status: str = "unknown"

    def apply_evidence(self, weight: float, metadata: Dict[str, Any]) -> None:
        """Blend new evidence into the hypothesis confidence."""
        # Basic exponential moving average to keep implementation simple.
        weight = max(0.0, min(weight, 1.0))
        self.confidence = (self.confidence * 0.7) + (weight * 0.3)
        self.evidence.update(metadata)
        self.last_updated = datetime.utcnow()


class WorldModel:
    """
    Shared situational awareness between Red/Blue teams.
    Maintains multiple competing hypotheses simultaneously.
    """

    def __init__(self) -> None:
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._history: List[Dict[str, Any]] = []

    def ingest_signal(self, signal: Dict[str, Any]) -> None:
        """Store raw signal data for later reference."""
        if not signal:
            return
        signal["timestamp"] = datetime.utcnow()
        self._history.append(signal)
        label = signal.get("label", "unknown")
        confidence = signal.get("confidence", 0.1)
        self.update_hypothesis(label, confidence, signal)

    def update_hypothesis(
        self,
        name: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Hypothesis:
        """Update or create a hypothesis."""
        hypothesis = self._hypotheses.get(name)
        if not hypothesis:
            hypothesis = Hypothesis(name=name, confidence=confidence)
            self._hypotheses[name] = hypothesis
        hypothesis.apply_evidence(confidence, metadata or {})
        return hypothesis

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a snapshot for UI consumption."""
        return {
            "hypotheses": {
                name: {
                    "confidence": round(hyp.confidence, 3),
                    "updated": hyp.last_updated.isoformat(),
                    "status": hyp.status,
                }
                for name, hyp in self._hypotheses.items()
            },
            "history_size": len(self._history),
        }

    def get_dominant_hypothesis(self) -> Optional[Hypothesis]:
        """Return the highest confidence hypothesis."""
        if not self._hypotheses:
            return None
        return max(self._hypotheses.values(), key=lambda h: h.confidence)

    def can_act(self) -> bool:
        """Actions are allowed only if a hypothesis exceeds 0.6 confidence."""
        dominant = self.get_dominant_hypothesis()
        return bool(dominant and dominant.confidence > 0.6)

    def reflect(self, outcome: Dict[str, Any]) -> None:
        """Feed back action outcomes into the model."""
        if not outcome:
            return
        label = outcome.get("label", "reflection")
        weight = outcome.get("confidence", 0.3)
        self.update_hypothesis(label, weight, outcome)
