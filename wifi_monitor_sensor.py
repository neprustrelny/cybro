"""Passive Wi-Fi monitor sensor backend for CYBRO WatchDog v7.0."""

from __future__ import annotations

import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional

try:
    from scapy.all import AsyncSniffer, Dot11, RadioTap
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("scapy is required for Wi-Fi monitoring") from exc


class WiFiMonitorSensor:
    """Passive Wi-Fi monitor using monitor-mode interface."""

    CHANNEL_LIST = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

    def __init__(
        self,
        interface: str = "wlan1",
        monitor_interface: Optional[str] = None,
        channel_dwell: float = 0.3,
    ):
        self.interface = interface
        self.monitor_interface = monitor_interface or f"{interface}mon"
        self.sniffer: Optional[AsyncSniffer] = None
        self._sniff_thread: Optional[threading.Thread] = None
        self._channel_thread: Optional[threading.Thread] = None
        self._presence_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.channel_dwell = channel_dwell
        self.current_channel: Optional[int] = None
        self.devices: Dict[str, Dict[str, object]] = {}
        self.events: list[Dict[str, object]] = []
        self.lost_timeout = 15.0

    def start(self) -> bool:
        if self.sniffer and self.sniffer.running:
            return True
        if not self._prepare_interface():
            return False
        self._stop_event.clear()
        self._sniff_thread = threading.Thread(target=self._sniff_loop, daemon=True)
        self._sniff_thread.start()
        self._channel_thread = threading.Thread(target=self._channel_hop_loop, daemon=True)
        self._channel_thread.start()
        self._presence_thread = threading.Thread(target=self._presence_loop, daemon=True)
        self._presence_thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self.sniffer and self.sniffer.running:
            self.sniffer.stop()
        if self._sniff_thread:
            self._sniff_thread.join(timeout=5)
        if self._channel_thread:
            self._channel_thread.join(timeout=5)
        if self._presence_thread:
            self._presence_thread.join(timeout=5)
        self._restore_interface()

    def _prepare_interface(self) -> bool:
        if not self._run_command(["sudo", "airmon-ng", "stop", self.monitor_interface], ignore_errors=True):
            pass
        if self._run_command(["sudo", "airmon-ng", "start", self.interface]):
            return True
        if self._run_command(["sudo", "ip", "link", "set", self.interface, "down"], ignore_errors=True):
            if self._run_command(["sudo", "iw", self.interface, "set", "monitor", "none"], ignore_errors=True) and self._run_command(["sudo", "ip", "link", "set", self.interface, "up"], ignore_errors=True):
                self.monitor_interface = self.interface
                return True
        return False

    def _restore_interface(self) -> None:
        self._run_command(["sudo", "airmon-ng", "stop", self.monitor_interface], ignore_errors=True)
        self._run_command(["sudo", "systemctl", "restart", "NetworkManager"], ignore_errors=True)

    def _sniff_loop(self) -> None:
        if self.sniffer and self.sniffer.running:
            return
        try:
            self.sniffer = AsyncSniffer(iface=self.monitor_interface, prn=self._handle_packet, store=False)
            self.sniffer.start()
            while not self._stop_event.is_set():
                time.sleep(0.5)
        finally:
            if self.sniffer and self.sniffer.running:
                self.sniffer.stop()

    def _handle_packet(self, packet) -> None:
        if not packet.haslayer(Dot11) or not packet.haslayer(RadioTap):
            return
        dot11 = packet[Dot11]
        radiotap = packet[RadioTap]
        mac = dot11.addr2 or dot11.addr1
        if not mac:
            return
        device_type = "ap" if dot11.type == 0 and dot11.subtype in {8, 5} else "station"
        rssi = getattr(radiotap, "dBm_AntSignal", None)
        channel = getattr(radiotap, "ChannelFrequency", None)
        now = datetime.now(timezone.utc)
        entry = self.devices.get(mac)
        if not entry:
            entry = {
                "mac": mac,
                "type": device_type,
                "rssi": rssi,
                "channel": channel,
                "band": "2.4GHz",
                "first_seen": now,
                "last_seen": now,
                "frame_count": 1,
                "present": True,
            }
            self.devices[mac] = entry
            self._record_event("WIFI_DEVICE_SEEN", entry)
        else:
            entry["last_seen"] = now
            entry["frame_count"] = int(entry["frame_count"]) + 1
            entry["rssi"] = rssi if rssi is not None else entry.get("rssi")
            entry["channel"] = channel if channel is not None else entry.get("channel")
            entry["type"] = entry["type"] or device_type
            if not entry.get("present"):
                entry["present"] = True
                self._record_event("WIFI_DEVICE_SEEN", entry)

    def _channel_hop_loop(self) -> None:
        if not self.CHANNEL_LIST:
            return
        index = 0
        while not self._stop_event.is_set():
            channel = self.CHANNEL_LIST[index]
            self._set_channel(channel)
            index = (index + 1) % len(self.CHANNEL_LIST)
            self._wait_with_stop(self.channel_dwell)

    def _set_channel(self, channel: int) -> None:
        if self._run_command(
            ["sudo", "iw", "dev", self.monitor_interface, "set", "channel", str(channel)],
            ignore_errors=True,
        ):
            self.current_channel = channel

    def _wait_with_stop(self, duration: float) -> None:
        end_time = time.time() + duration
        while time.time() < end_time and not self._stop_event.is_set():
            time.sleep(0.05)

    def _presence_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._evaluate_presence()
            except Exception:
                pass
            self._wait_with_stop(1.0)

    def _evaluate_presence(self) -> None:
        now = datetime.now(timezone.utc)
        for entry in list(self.devices.values()):
            last_seen = entry.get("last_seen")
            if not entry.get("present"):
                continue
            if isinstance(last_seen, datetime) and (now - last_seen).total_seconds() > self.lost_timeout:
                entry["present"] = False
                self._record_event("WIFI_DEVICE_LOST", entry)

    def _record_event(self, event_type: str, entry: Dict[str, object]) -> None:
        payload = {
            "event": event_type,
            "mac": entry.get("mac"),
            "timestamp": datetime.now(timezone.utc),
            "rssi": entry.get("rssi"),
            "channel": entry.get("channel"),
        }
        self.events.append(payload)

    def _run_command(self, cmd, ignore_errors: bool = False) -> bool:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            if ignore_errors:
                return False
            return False
