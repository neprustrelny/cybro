from __future__ import annotations

from datetime import datetime, timezone, timedelta
from threading import RLock
from typing import Any, Dict, Iterable, Optional


class PresenceWatchdogSensor:
    """Keeps lightweight presence metrics for decision loop + UI."""

    name = "presence_watchdog"

    def __init__(self, stale_seconds: int = 300):
        self.stale_seconds = stale_seconds
        self._lock = RLock()
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._last_event: Optional[Dict[str, Any]] = None
        self._last_tick: Optional[datetime] = None

    def feed_devices(self, devices: Iterable[Dict[str, Any]]) -> None:
        """Update internal state from a device snapshot."""
        now = datetime.now(timezone.utc)
        with self._lock:
            for device in devices or []:
                mac = (device.get("mac") or device.get("MAC") or "").upper()
                if not mac:
                    continue
                last_seen = self._normalize_timestamp(device.get("last_seen")) or now
                self._devices[mac] = {
                    "mac": mac,
                    "ip": device.get("ip"),
                    "hostname": device.get("hostname")
                    or device.get("host")
                    or "Unknown",
                    "vendor": device.get("vendor"),
                    "last_seen": last_seen,
                }
            self._prune(now)
            self._last_tick = now

    def record_event(self, event: Any) -> None:
        """Store the latest passive sensor event for diagnostics."""
        if not event:
            return
        with self._lock:
            if isinstance(event, dict):
                event_type = event.get("event_type") or event.get("event")
                mac = event.get("mac")
                timestamp = event.get("timestamp")
            else:
                event_type = getattr(event, "event_type", None)
                mac = getattr(event, "mac", None)
                timestamp = getattr(event, "timestamp", None)
                if hasattr(event_type, "value"):
                    event_type = event_type.value
                elif event_type is not None and not isinstance(event_type, str):
                    event_type = str(event_type)

            ts: Optional[datetime] = None
            if isinstance(timestamp, datetime):
                ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            elif isinstance(timestamp, str):
                ts = self._normalize_timestamp(timestamp)
            if ts is None:
                ts = datetime.now(timezone.utc)

            self._last_event = {
                "event": event_type,
                "mac": mac,
                "timestamp": ts.isoformat(),
            }
            self._last_tick = datetime.now(timezone.utc)

    def collect(self) -> Dict[str, Any]:
        """Expose summarized presence data to the decision loop."""
        now = datetime.now(timezone.utc)
        with self._lock:
            active = [
                info
                for info in self._devices.values()
                if (now - info.get("last_seen", now)).total_seconds() <= self.stale_seconds
            ]
            confidence = 0.3 + min(len(active) / 40.0, 0.6)
            return {
                "label": self.name,
                "confidence": round(confidence, 2),
                "active_devices": len(active),
                "known_devices": len(self._devices),
                "last_event": self._last_event,
                "last_update": self._last_tick.isoformat() if self._last_tick else None,
            }

    def _prune(self, now: datetime) -> None:
        expire_before = now - timedelta(seconds=self.stale_seconds)
        self._devices = {
            mac: info
            for mac, info in self._devices.items()
            if info.get("last_seen", now) >= expire_before
        }

    @staticmethod
    def _normalize_timestamp(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None
