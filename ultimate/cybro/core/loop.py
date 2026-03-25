from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Optional

from .state import WorldModel
from .permissions import PrivilegeManager
from .audit import AuditLogger


@dataclass
class Decision:
    label: str
    context: Dict[str, Any]
    intent: Any
    blue_posture: str
    allowed: bool


class DecisionLoop:
    """
    Implements the SENSE → MODEL → DECIDE → ACT → REFLECT loop.
    All risky actions must go through execute_action.
    """

    def __init__(
        self,
        *,
        sensors: List[Any],
        world_model: WorldModel,
        red_engine: Any,
        blue_engine: Any,
        campaign_engine: Any,
        deception_engine: Any,
        ai_debate: Any,
        audit_logger: AuditLogger,
        permissions: PrivilegeManager,
    ) -> None:
        self.sensors = sensors
        self.world_model = world_model
        self.red_engine = red_engine
        self.blue_engine = blue_engine
        self.campaign_engine = campaign_engine
        self.deception_engine = deception_engine
        self.ai_debate = ai_debate
        self.audit_logger = audit_logger
        self.permissions = permissions
        self.lock = threading.RLock()
        self._ui = None

    def attach_ui(self, ui_ref: Any) -> None:
        self._ui = ui_ref

    def sense(self) -> List[Dict[str, Any]]:
        observations = []
        for sensor in self.sensors:
            try:
                data = sensor.collect()
                if data:
                    observations.append(data)
            except PermissionError as exc:
                self.audit_logger.log_decision(
                    {"phase": "sense", "sensor": sensor.name, "error": str(exc)}
                )
        return observations

    def model(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        for obs in observations:
            self.world_model.ingest_signal(obs)
        return self.world_model.get_snapshot()

    def decide(self, label: str, context: Dict[str, Any]) -> Decision:
        intent = self.red_engine.build_intent(self.world_model, label, context)
        posture = self.blue_engine.evaluate_posture(self.world_model, intent)
        allowed = self.world_model.can_act()
        return Decision(
            label=label,
            context=context,
            intent=intent,
            blue_posture=posture,
            allowed=allowed,
        )

    def act(
        self, decision: Decision, action_callable: Callable[[], Any]
    ) -> Dict[str, Any]:
        if decision.blue_posture == "passive":
            result = action_callable()
        elif decision.blue_posture == "deceptive":
            # Deception engine may inject fake assets alongside the action.
            fake_asset = self.deception_engine.deploy_decoy(decision.context)
            result = action_callable()
            self.deception_engine.clear_decoy(fake_asset)
        else:  # aggressive posture
            self.blue_engine.delay_response(decision.context)
            result = action_callable()
        return {"result": result, "intent": decision.intent}

    def reflect(self, decision: Decision, outcome: Dict[str, Any], ai_report: Dict[str, Any]) -> None:
        reflection = {
            "label": f"reflect::{decision.label}",
            "confidence": outcome.get("confidence", 0.4),
            "details": {"ai_feedback": ai_report, "intent": decision.intent},
        }
        self.world_model.reflect(reflection)
        self.audit_logger.log_decision(
            {
                "phase": "reflect",
                "label": decision.label,
                "result": outcome.get("result"),
                "ai_feedback": ai_report,
            }
        )

    def execute_action(
        self,
        label: str,
        context: Optional[Dict[str, Any]],
        action_callable: Callable[[], Any],
    ) -> Any:
        """Public API used by UI components to execute privileged actions."""
        context = context or {}
        with self.lock:
            observations = self.sense()
            snapshot = self.model(observations)
            decision = self.decide(label, context | {"world": snapshot})
            if not decision.allowed:
                raise PermissionError("World model confidence too low to act.")

            ai_feedback = self.ai_debate.challenge(decision, context)
            if ai_feedback.get("bias"):
                self.audit_logger.log_bias(ai_feedback)

            self.audit_logger.log_decision(
                {
                    "phase": "decide",
                    "label": label,
                    "intent": decision.intent.to_dict(),
                    "blue_posture": decision.blue_posture,
                    "ai_feedback": ai_feedback,
                }
            )

            outcome = self.act(decision, action_callable)
            self.reflect(decision, outcome, ai_feedback)
            self.campaign_engine.record_action(label, decision.intent)
            return outcome["result"]
