"""
Device registry and OUI lookup for CYBRO WatchDog's passive sensor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
import csv
import logging
import re

from passive_capture import NetworkObservation
from storage import DeviceStorage, StoredDevice


def normalize_mac(mac: Optional[str]) -> Optional[str]:
    if not mac:
        return None
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", mac)
    if len(cleaned) != 12:
        return mac.upper()
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2)).upper()


@dataclass
class DeviceRecord:
    mac: str
    vendor: Optional[str]
    first_seen: datetime
    last_seen: datetime
    seen_count: int
    last_ip: Optional[str] = None
    ip_history: List[str] = field(default_factory=list)
    hostnames: Set[str] = field(default_factory=set)
    last_hostname: Optional[str] = None
    online: bool = True
    protocols: Set[str] = field(default_factory=set)


class DeviceStatus:
    NEW = "NEW"
    UPDATED = "UPDATED"
    REAPPEARED = "REAPPEARED"


@dataclass
class RegistryUpdateResult:
    device: DeviceRecord
    status: str
    ip_changed: bool
    hostname_updated: bool
    observation: NetworkObservation


class OUIResolver:
    """Offline vendor resolver backed by CSV."""

    def __init__(self, db_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent
        default_path = base_dir / "oui_sample.csv"
        self.db_path = Path(db_path) if db_path else default_path
        self._mapping: Dict[str, str] = {}
        self._cache: Dict[str, Optional[str]] = {}
        self.logger = logging.getLogger("cybro.oui")
        if self.db_path.exists():
            self._load()
        else:
            self.logger.warning(
                "OUI database %s not found. Vendor lookups limited.", self.db_path
            )

    def _load(self) -> None:
        with self.db_path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if not row or row[0].startswith("#") or len(row) < 2:
                    continue
                prefix = re.sub(r"[^0-9A-Fa-f]", "", row[0])[:6].upper()
                if len(prefix) == 6:
                    self._mapping[prefix] = row[1].strip()

    def lookup(self, mac: Optional[str]) -> Optional[str]:
        normalized = normalize_mac(mac)
        if not normalized:
            return None
        prefix = normalized.replace(":", "")[:6]
        if prefix in self._cache:
            return self._cache[prefix]
        vendor = self._mapping.get(prefix)
        self._cache[prefix] = vendor
        return vendor


class DeviceRegistry:
    """Stateful registry that merges live observations with SQLite history."""

    def __init__(
        self,
        storage: DeviceStorage,
        vendor_resolver: Optional[OUIResolver] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.storage = storage
        self.vendor_resolver = vendor_resolver or OUIResolver()
        self.logger = logger or logging.getLogger("cybro.device_registry")
        self.devices: Dict[str, DeviceRecord] = {}
        self._load_from_storage()

    def _load_from_storage(self) -> None:
        stored = self.storage.load_devices()
        for mac, entry in stored.items():
            if not entry.first_seen:
                continue
            record = DeviceRecord(
                mac=mac,
                vendor=entry.vendor,
                first_seen=entry.first_seen,
                last_seen=entry.last_seen or entry.first_seen,
                seen_count=entry.seen_count,
                last_ip=entry.last_ip,
                ip_history=list(dict.fromkeys(entry.ip_history)),
                hostnames=set(entry.hostnames),
                last_hostname=entry.hostnames[0] if entry.hostnames else None,
                online=False,
            )
            self.devices[mac] = record
        self.logger.info("Loaded %d devices from passive history", len(self.devices))

    def ingest_observation(
        self, observation: NetworkObservation
    ) -> Optional[RegistryUpdateResult]:
        mac = normalize_mac(observation.mac)
        if not mac:
            return None

        record = self.devices.get(mac)
        timestamp = observation.timestamp
        ip_changed = False
        hostname_updated = False

        if not record:
            vendor = self.vendor_resolver.lookup(mac)
            record = DeviceRecord(
                mac=mac,
                vendor=vendor,
                first_seen=timestamp,
                last_seen=timestamp,
                seen_count=1,
                last_ip=observation.ip,
                ip_history=[observation.ip] if observation.ip else [],
                hostnames=set(filter(None, [observation.hostname])),
                last_hostname=observation.hostname,
                protocols={observation.protocol},
            )
            self.devices[mac] = record
            status = DeviceStatus.NEW
        else:
            status = DeviceStatus.UPDATED
            if not record.online:
                status = DeviceStatus.REAPPEARED
            record.online = True
            record.last_seen = timestamp
            record.seen_count += 1
            record.protocols.add(observation.protocol)
            if observation.ip and observation.ip != record.last_ip:
                ip_changed = True
                record.last_ip = observation.ip
                if observation.ip not in record.ip_history:
                    record.ip_history.append(observation.ip)

        if observation.hostname:
            hostname = observation.hostname.strip()
            if hostname and hostname not in record.hostnames:
                hostname_updated = True
                record.hostnames.add(hostname)
            record.last_hostname = hostname or record.last_hostname

        self.storage.upsert_device(
            mac=record.mac,
            vendor=record.vendor,
            first_seen=record.first_seen,
            last_seen=record.last_seen,
            seen_count=record.seen_count,
            last_ip=record.last_ip,
            hostname=record.last_hostname,
        )
        if observation.ip:
            self.storage.record_ip(record.mac, observation.ip, timestamp)
        if observation.hostname:
            self.storage.record_hostname(record.mac, observation.hostname, timestamp)

        return RegistryUpdateResult(
            device=record,
            status=status,
            ip_changed=ip_changed,
            hostname_updated=hostname_updated,
            observation=observation,
        )

    def detect_timeouts(self, timeout: timedelta) -> List[DeviceRecord]:
        now = datetime.now(timezone.utc)
        expired: List[DeviceRecord] = []
        for record in self.devices.values():
            if not record.online:
                continue
            if record.last_seen + timeout < now:
                record.online = False
                expired.append(record)
        return expired

    def all_devices(self) -> List[DeviceRecord]:
        return list(self.devices.values())

