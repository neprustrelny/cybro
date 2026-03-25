"""Wi-Fi presence panel for CYBRO WatchDog v7.0."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional


class WiFiPresencePanel:
    """Tkinter panel showing Wi-Fi presence and events."""

    def __init__(self, parent: tk.Frame, sensor) -> None:
        self.parent = parent
        self.sensor = sensor
        self.root = parent.winfo_toplevel()
        self._setup_ui()
        self.refresh_interval_ms = 1500
        self._schedule_refresh()

    def _setup_ui(self) -> None:
        container = tk.Frame(self.parent, bg="#1a1a2e")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        devices_frame = tk.LabelFrame(
            container,
            text="📡 Wi-Fi Devices",
            bg="#1a1a2e",
            fg="#00ff9d",
            font=("Courier New", 12, "bold"),
        )
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("mac", "type", "rssi", "channel", "status", "last_seen")
        self.devices_tree = ttk.Treeview(devices_frame, columns=columns, show="headings", height=12)
        headings = {
            "mac": "MAC",
            "type": "Type",
            "rssi": "RSSI",
            "channel": "Channel",
            "status": "Status",
            "last_seen": "Last Seen",
        }
        for col, title in headings.items():
            self.devices_tree.heading(col, text=title)
            width = 140 if col == "mac" else 90
            self.devices_tree.column(col, width=width, anchor=tk.CENTER)
        self.devices_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        events_frame = tk.LabelFrame(
            container,
            text="📃 Recent Wi-Fi Events",
            bg="#1a1a2e",
            fg="#00ff9d",
            font=("Courier New", 12, "bold"),
        )
        events_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        event_columns = ("timestamp", "event", "mac", "rssi", "channel")
        self.events_tree = ttk.Treeview(events_frame, columns=event_columns, show="headings", height=8)
        event_headings = {
            "timestamp": "Timestamp",
            "event": "Event",
            "mac": "MAC",
            "rssi": "RSSI",
            "channel": "Channel",
        }
        for col, title in event_headings.items():
            width = 150 if col == "timestamp" else 110
            self.events_tree.heading(col, text=title)
            self.events_tree.column(col, width=width, anchor=tk.CENTER)
        self.events_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _schedule_refresh(self) -> None:
        self.root.after(self.refresh_interval_ms, self._refresh_data)

    def _refresh_data(self) -> None:
        try:
            self._update_devices()
            self._update_events()
        except Exception:
            pass
        finally:
            self._schedule_refresh()

    def _update_devices(self) -> None:
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        devices = getattr(self.sensor, "devices", {})
        for entry in devices.values():
            mac = entry.get("mac", "?")
            status = "PRESENT" if entry.get("present") else "LOST"
            last_seen = entry.get("last_seen")
            if isinstance(last_seen, datetime):
                last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_seen_str = "?"
            self.devices_tree.insert(
                "",
                tk.END,
                values=(
                    mac,
                    entry.get("type") or "?",
                    entry.get("rssi"),
                    entry.get("channel"),
                    status,
                    last_seen_str,
                ),
            )

    def _update_events(self) -> None:
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        events = getattr(self.sensor, "events", [])
        recent = events[-50:]
        for event in reversed(recent):
            timestamp = event.get("timestamp")
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.strftime("%H:%M:%S")
            else:
                timestamp_str = "?"
            self.events_tree.insert(
                "",
                tk.END,
                values=(
                    timestamp_str,
                    event.get("event", ""),
                    event.get("mac", ""),
                    event.get("rssi"),
                    event.get("channel"),
                ),
            )
