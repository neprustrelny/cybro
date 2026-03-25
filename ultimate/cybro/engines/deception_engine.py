from __future__ import annotations

import random
from typing import Dict, Any, Optional


class DeceptionEngine:
    """Creates reversible fake assets (ARP hosts, BLE beacons, ports)."""

    def __init__(self, audit_logger) -> None:
        self.audit_logger = audit_logger
        self.active_decoys: Dict[str, Dict[str, Any]] = {}

    def _generate_identifier(self) -> str:
        return f"decoy-{random.randint(1000, 9999)}"

    def deploy_decoy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        decoy_id = self._generate_identifier()
        asset_type = context.get("asset_type", "arp")
        decoy = {
            "id": decoy_id,
            "type": asset_type,
            "details": {
                "ip": context.get("ip", f"10.0.0.{random.randint(10, 250)}"),
                "mac": context.get("mac", "de:co:y0:00:00"),
                "port": context.get("port", random.randint(1024, 65535)),
                "ble_name": context.get("ble_name", "CYBRO_DECOY"),
            },
        }
        self.active_decoys[decoy_id] = decoy
        self.audit_logger.log_decision({"phase": "decoy_deploy", "decoy": decoy})
        return decoy

    def clear_decoy(self, decoy: Optional[Dict[str, Any]]) -> None:
        if not decoy:
            return
        self.active_decoys.pop(decoy["id"], None)
        self.audit_logger.log_decision({"phase": "decoy_clear", "decoy": decoy})
