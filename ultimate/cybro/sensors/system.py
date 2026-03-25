from __future__ import annotations

import os
from typing import Dict, Any

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


class SystemSensor:
    """Captures OS/process level signals."""

    name = "system"

    def collect(self) -> Dict[str, Any]:
        load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
        mem = psutil.virtual_memory().percent if psutil else 0.0
        confidence = 0.7 if load < 1.5 else 0.4
        return {
            "label": "system_health",
            "confidence": confidence,
            "load": load,
            "memory_percent": mem,
        }
