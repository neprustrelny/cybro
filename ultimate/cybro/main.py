from __future__ import annotations

from pathlib import Path

from .core.state import WorldModel
from .core.loop import DecisionLoop
from .core.permissions import PrivilegeManager
from .core.audit import AuditLogger
from .engines.red_engine import RedEngine
from .engines.blue_engine import BlueEngine
from .engines.campaign_engine import CampaignEngine
from .engines.deception_engine import DeceptionEngine
from .sensors.network import NetworkSensor
from .sensors.ble import BLESensor
from .sensors.system import SystemSensor
from .sensors.presence_watchdog import PresenceWatchdogSensor
from .ai.debate import AIDebate
from .ui.dashboard import launch_ui


def build_decision_loop() -> DecisionLoop:
    permissions = PrivilegeManager()
    audit_logger = AuditLogger(Path.cwd() / "logs")
    world_model = WorldModel()
    presence_watchdog = PresenceWatchdogSensor()
    sensors = [
        NetworkSensor(permissions),
        BLESensor(permissions),
        SystemSensor(),
        presence_watchdog,
    ]
    red_engine = RedEngine()
    blue_engine = BlueEngine()
    campaign_engine = CampaignEngine(audit_logger)
    deception_engine = DeceptionEngine(audit_logger)
    ai_debate = AIDebate(audit_logger)

    decision_loop = DecisionLoop(
        sensors=sensors,
        world_model=world_model,
        red_engine=red_engine,
        blue_engine=blue_engine,
        campaign_engine=campaign_engine,
        deception_engine=deception_engine,
        ai_debate=ai_debate,
        audit_logger=audit_logger,
        permissions=permissions,
    )
    decision_loop.presence_watchdog = presence_watchdog
    return decision_loop


def main():
    decision_loop = build_decision_loop()
    launch_ui(decision_loop)


if __name__ == "__main__":
    main()
