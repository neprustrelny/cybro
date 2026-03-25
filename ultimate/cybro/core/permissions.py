from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PrivilegeProfile:
    """Simple permission profile distinguishing operator/root contexts."""

    is_root: bool
    network_allowed: bool
    ai_network_allowed: bool


class PrivilegeManager:
    """
    Handles privilege separation rules:
    - Core logic: user mode
    - Sensors: escalate only when required
    - AI: sandboxed, no network access
    """

    def __init__(self) -> None:
        self.profile = PrivilegeProfile(
            is_root=os.geteuid() == 0,
            network_allowed=True,
            ai_network_allowed=False,
        )

    def require_root_for_sensor(self, sensor_name: str) -> None:
        """Raise if a privileged sensor is invoked as user."""
        if not self.profile.is_root:
            raise PermissionError(
                f"Sensor '{sensor_name}' requires elevated privileges."
            )

    def run_as_operator(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """
        Execute a subprocess using operator privileges.
        This method exists to centralize auditing in core.loop.
        """
        kwargs.setdefault("text", True)
        return subprocess.run(cmd, **kwargs)

    def sandbox_ai_call(self, fn, *args, **kwargs):
        """AI helpers must never access the network."""
        if kwargs.get("allow_network"):
            raise PermissionError("AI modules are sandboxed; network disabled.")
        return fn(*args, **kwargs)

    def describe(self) -> Dict[str, Any]:
        return {
            "is_root": self.profile.is_root,
            "network_allowed": self.profile.network_allowed,
            "ai_network_allowed": self.profile.ai_network_allowed,
        }
