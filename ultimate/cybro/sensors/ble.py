from __future__ import annotations

try:
    from bleak import BleakScanner
except ImportError:  # pragma: no cover - bleak optional
    BleakScanner = None


class BLESensor:
    """Samples BLE environment for beacon density."""

    name = "ble"

    def __init__(self, permissions) -> None:
        self.permissions = permissions

    def collect(self):
        if not BleakScanner:
            return {"label": "ble_passive", "confidence": 0.3, "devices": []}
        # Sensing operations use short scans without exposing network.
        devices = []
        try:
            scan = BleakScanner()
            devices = getattr(scan, "discovered_devices", [])
        except Exception:
            devices = []
        confidence = 0.5 if devices else 0.2
        return {"label": "ble_presence", "confidence": confidence, "devices": len(devices)}
