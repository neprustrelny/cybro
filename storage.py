"""
SQLite persistence for CYBRO WatchDog's passive sensor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3
import threading


def _ts(value: datetime) -> str:
    return value.isoformat()


def _from_ts(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


@dataclass
class StoredDevice:
    mac: str
    vendor: Optional[str]
    first_seen: datetime
    last_seen: datetime
    seen_count: int
    last_ip: Optional[str]
    hostnames: List[str]
    ip_history: List[str]


class DeviceStorage:
    """Thin wrapper around sqlite3 for device history."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    mac TEXT PRIMARY KEY,
                    vendor TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    seen_count INTEGER NOT NULL,
                    last_ip TEXT,
                    last_hostname TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_ips (
                    mac TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    seen_count INTEGER NOT NULL,
                    PRIMARY KEY(mac, ip)
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_hostnames (
                    mac TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    seen_count INTEGER NOT NULL,
                    PRIMARY KEY(mac, hostname)
                )
                """
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def load_devices(self) -> Dict[str, StoredDevice]:
        with self._lock:
            device_rows = self._conn.execute("SELECT * FROM devices").fetchall()
            ip_rows = self._conn.execute(
                "SELECT mac, ip FROM device_ips ORDER BY last_seen DESC"
            ).fetchall()
            hostname_rows = self._conn.execute(
                "SELECT mac, hostname FROM device_hostnames ORDER BY last_seen DESC"
            ).fetchall()

        ip_map: Dict[str, List[str]] = {}
        for row in ip_rows:
            ip_map.setdefault(row["mac"], []).append(row["ip"])

        hostname_map: Dict[str, List[str]] = {}
        for row in hostname_rows:
            hostname_map.setdefault(row["mac"], []).append(row["hostname"])

        devices: Dict[str, StoredDevice] = {}
        for row in device_rows:
            mac = row["mac"]
            devices[mac] = StoredDevice(
                mac=mac,
                vendor=row["vendor"],
                first_seen=_from_ts(row["first_seen"]),
                last_seen=_from_ts(row["last_seen"]),
                seen_count=row["seen_count"],
                last_ip=row["last_ip"],
                hostnames=hostname_map.get(mac, []),
                ip_history=ip_map.get(mac, []),
            )
        return devices

    def upsert_device(
        self,
        mac: str,
        vendor: Optional[str],
        first_seen: datetime,
        last_seen: datetime,
        seen_count: int,
        last_ip: Optional[str],
        hostname: Optional[str],
    ) -> None:
        payload = {
            "mac": mac,
            "vendor": vendor,
            "first_seen": _ts(first_seen),
            "last_seen": _ts(last_seen),
            "seen_count": seen_count,
            "last_ip": last_ip,
            "last_hostname": hostname,
        }
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO devices (mac, vendor, first_seen, last_seen, seen_count, last_ip, last_hostname)
                VALUES (:mac, :vendor, :first_seen, :last_seen, :seen_count, :last_ip, :last_hostname)
                ON CONFLICT(mac) DO UPDATE SET
                    vendor=excluded.vendor,
                    last_seen=excluded.last_seen,
                    seen_count=excluded.seen_count,
                    last_ip=excluded.last_ip,
                    last_hostname=excluded.last_hostname
                """,
                payload,
            )

    def record_ip(self, mac: str, ip: str, timestamp: datetime) -> None:
        payload = {"mac": mac, "ip": ip, "ts": _ts(timestamp)}
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO device_ips (mac, ip, first_seen, last_seen, seen_count)
                VALUES (:mac, :ip, :ts, :ts, 1)
                ON CONFLICT(mac, ip) DO UPDATE SET
                    last_seen=excluded.last_seen,
                    seen_count=device_ips.seen_count + 1
                """,
                payload,
            )

    def record_hostname(self, mac: str, hostname: str, timestamp: datetime) -> None:
        payload = {"mac": mac, "hostname": hostname, "ts": _ts(timestamp)}
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO device_hostnames (mac, hostname, first_seen, last_seen, seen_count)
                VALUES (:mac, :hostname, :ts, :ts, 1)
                ON CONFLICT(mac, hostname) DO UPDATE SET
                    last_seen=excluded.last_seen,
                    seen_count=device_hostnames.seen_count + 1
                """,
                payload,
            )

    def get_ip_history(self, mac: str) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ip FROM device_ips WHERE mac=? ORDER BY last_seen DESC", (mac,)
            ).fetchall()
        return [row["ip"] for row in rows]

    def get_hostname_history(self, mac: str) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT hostname FROM device_hostnames WHERE mac=? ORDER BY last_seen DESC",
                (mac,),
            ).fetchall()
        return [row["hostname"] for row in rows]

