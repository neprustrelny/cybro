"""
Event engine gluing passive capture to the device registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional
import enum
import json
import logging
import threading
import time

from passive_capture import NetworkObservation, PassiveCapture
from device_registry import DeviceRegistry, DeviceStatus


class DeviceEventType(enum.Enum):
    NEW_DEVICE = "NEW_DEVICE"
    DEVICE_REAPPEARED = "DEVICE_REAPPEARED"
    DEVICE_DISAPPEARED = "DEVICE_DISAPPEARED"
    IP_CHANGED = "IP_CHANGED"
    OBSERVATION = "OBSERVATION"


@dataclass
class DeviceEvent:
    event_type: DeviceEventType
    mac: str
    timestamp: datetime
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "mac": self.mac,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }

    def __str__(self) -> str:  # pragma: no cover - helper
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventEngine:
    """Consumes packet observations and emits structured device events."""

    def __init__(
        self,
        capture: PassiveCapture,
        registry: DeviceRegistry,
        observation_queue: Optional[Queue] = None,
        disappearance_timeout: int = 900,
        logger: Optional[logging.Logger] = None,
    ):
        self.capture = capture
        self.registry = registry
        self.observation_queue = observation_queue or capture.observation_queue
        self.disappearance_timeout = disappearance_timeout
        self.logger = logger or logging.getLogger("cybro.event_engine")
        self.listeners: List[Callable[[DeviceEvent], None]] = []
        self._running = threading.Event()
        self._observation_thread: Optional[threading.Thread] = None
        self._timeout_thread: Optional[threading.Thread] = None

    def register_listener(self, callback: Callable[[DeviceEvent], None]) -> None:
        self.listeners.append(callback)

    def start(self) -> None:
        if self._running.is_set():
            return
        self.logger.info("Starting passive event engine")
        self._running.set()
        self.capture.start()
        self._observation_thread = threading.Thread(
            target=self._consume_observations,
            name="cybro-passive-observer",
            daemon=True,
        )
        self._observation_thread.start()
        self._timeout_thread = threading.Thread(
            target=self._timeout_monitor,
            name="cybro-passive-timeouts",
            daemon=True,
        )
        self._timeout_thread.start()

    def stop(self) -> None:
        if not self._running.is_set():
            return
        self.logger.info("Stopping passive event engine")
        self._running.clear()
        self.capture.stop()
        if self._observation_thread:
            self._observation_thread.join(timeout=2)
        if self._timeout_thread:
            self._timeout_thread.join(timeout=2)

    def _consume_observations(self) -> None:
        while self._running.is_set():
            try:
                observation: NetworkObservation = self.observation_queue.get(timeout=1)
            except Empty:
                continue
            result = self.registry.ingest_observation(observation)
            if not result:
                continue

            self._emit(
                DeviceEvent(
                    event_type=DeviceEventType.OBSERVATION,
                    mac=result.device.mac,
                    timestamp=observation.timestamp,
                    payload={
                        "protocol": observation.protocol,
                        "ip": observation.ip,
                        "hostname": observation.hostname,
                        "vendor": result.device.vendor,
                    },
                )
            )

            if result.status == DeviceStatus.NEW:
                self._emit(
                    DeviceEvent(
                        event_type=DeviceEventType.NEW_DEVICE,
                        mac=result.device.mac,
                        timestamp=observation.timestamp,
                        payload=self._device_payload(result),
                    )
                )
            elif result.status == DeviceStatus.REAPPEARED:
                self._emit(
                    DeviceEvent(
                        event_type=DeviceEventType.DEVICE_REAPPEARED,
                        mac=result.device.mac,
                        timestamp=observation.timestamp,
                        payload=self._device_payload(result),
                    )
                )

            if result.ip_changed:
                self._emit(
                    DeviceEvent(
                        event_type=DeviceEventType.IP_CHANGED,
                        mac=result.device.mac,
                        timestamp=observation.timestamp,
                        payload={
                            "new_ip": result.device.last_ip,
                            "ip_history": result.device.ip_history,
                        },
                    )
                )

    def _timeout_monitor(self) -> None:
        timeout_delta = timedelta(seconds=self.disappearance_timeout)
        while self._running.is_set():
            expired = self.registry.detect_timeouts(timeout_delta)
            for record in expired:
                self._emit(
                    DeviceEvent(
                        event_type=DeviceEventType.DEVICE_DISAPPEARED,
                        mac=record.mac,
                        timestamp=datetime.now(timezone.utc),
                        payload=self._device_payload_from_record(record),
                    )
                )
            self._sleep_with_shutdown(max(5.0, timeout_delta.total_seconds() / 3))

    def _device_payload(self, result) -> Dict[str, Any]:
        return self._device_payload_from_record(result.device) | {
            "status": result.status,
            "hostname_updated": result.hostname_updated,
        }

    @staticmethod
    def _device_payload_from_record(record) -> Dict[str, Any]:
        return {
            "ip": record.last_ip,
            "hostnames": sorted(record.hostnames),
            "vendor": record.vendor,
            "first_seen": record.first_seen.isoformat(),
            "last_seen": record.last_seen.isoformat(),
            "seen_count": record.seen_count,
            "ip_history": record.ip_history,
            "protocols": sorted(record.protocols),
        }

    def _emit(self, event: DeviceEvent) -> None:
        self.logger.debug("Event emitted: %s", event)
        for listener in list(self.listeners):
            try:
                listener(event)
            except Exception:  # pragma: no cover - listeners are user code
                self.logger.exception("Passive sensor listener raised")

    def _sleep_with_shutdown(self, duration: float) -> None:
        deadline = time.time() + duration
        while self._running.is_set() and time.time() < deadline:
            time.sleep(0.5)

