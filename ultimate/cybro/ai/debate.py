from __future__ import annotations

from typing import Dict, Any

from .bias_checks import detect_biases


class AIDebate:
    """AI adversarial debate loop."""

    def __init__(self, audit_logger) -> None:
        self.audit_logger = audit_logger

    def challenge(self, decision, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide at least one counter-argument per decision.
        This is intentionally lightweight to avoid external dependencies.
        """
        counter_argument = self._build_counter_argument(decision, context)
        biases = detect_biases(decision.to_dict(), counter_argument)
        report = {"counter_argument": counter_argument, "bias": biases}
        if biases:
            self.audit_logger.log_bias({"decision": decision.label, "biases": biases})
        return report

    def _build_counter_argument(self, decision, context: Dict[str, Any]) -> str:
        if decision.intent.exposure_risk > 0.5:
            return "Exposure risk is high; consider delaying until Blue posture stabilizes."
        if decision.blue_posture == "aggressive":
            return "Blue posture is aggressive; acting now may burn access."
        if not context:
            return "Insufficient context supplied; action may be misaligned with objectives."
        return "Validate objective alignment and confirm stealth budget before acting."
