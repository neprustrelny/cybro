from __future__ import annotations

import subprocess
from typing import Dict, Any


class NetworkSensor:
    """Collects ARP/traffic signals using linux utilities."""

    name = "network"

    def __init__(self, permissions) -> None:
        self.permissions = permissions

    def collect(self) -> Dict[str, Any]:
        """Return gateway and interface state."""
        try:
            route = subprocess.check_output(["ip", "route"], text=True)
        except Exception:
            route = ""
        try:
            arp = subprocess.check_output(["ip", "neigh"], text=True)
        except Exception:
            arp = ""
        confidence = 0.4 if "default" in route else 0.2
        return {
            "label": "network_visibility",
            "confidence": confidence,
            "route_sample": route.splitlines()[:5],
            "arp_entries": arp.splitlines()[:5],
        }
