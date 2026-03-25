from __future__ import annotations

import math
import tkinter as tk
from datetime import datetime
from typing import Iterable, Optional


class NetworkMapWidget:
    """Simple canvas-based topology map for the network analyzer view."""

    def __init__(self, colors):
        self.colors = colors
        self.canvas: Optional[tk.Canvas] = None
        self._latest_devices: list[dict] = []
        self._device_nodes: dict[str, int] = {}
        self._status_text: Optional[int] = None
        self._pending_highlight: Optional[tuple[str, str]] = None
        self._dimensions = (780, 260)

    def attach(self, parent: tk.Widget) -> None:
        """Create the canvas widget inside the provided container."""
        if self.canvas:
            self.canvas.destroy()
        width, height = self._dimensions
        self.canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=self.colors["background"],
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._draw_backdrop()
        self._render_devices()

    def update_devices(self, devices: Iterable[dict]) -> None:
        """Store device snapshot and refresh the map."""
        self._latest_devices = list(devices or [])
        self._render_devices()

    def highlight_device(self, mac: Optional[str], status: str) -> None:
        """Pulse a node outline based on a passive sensor event."""
        mac = (mac or "").upper()
        if not mac:
            return
        if not self.canvas:
            self._pending_highlight = (mac, status)
            return

        node_id = self._device_nodes.get(mac)
        color = self._status_color(status)
        if node_id:
            self.canvas.itemconfigure(node_id, outline=color, width=3)
            self.canvas.after(
                1200,
                lambda nid=node_id: self.canvas and self.canvas.itemconfigure(
                    nid, outline=self.colors["background"], width=1
                ),
            )
        else:
            # Store highlight for when the node is eventually drawn.
            self._pending_highlight = (mac, status)

        msg = f"{status.replace('_', ' ').title()} · {mac}"
        self._show_status(msg, color)

    def _render_devices(self) -> None:
        if not self.canvas:
            return
        width = max(self.canvas.winfo_width(), self._dimensions[0])
        height = max(self.canvas.winfo_height(), self._dimensions[1])
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2.5

        self.canvas.delete("device")
        self._device_nodes.clear()
        self._draw_backdrop()

        if not self._latest_devices:
            self._show_status("Waiting for network activity…", self.colors["text_secondary"])
            return

        for idx, device in enumerate(self._latest_devices):
            mac = (device.get("mac") or device.get("MAC") or f"device-{idx}").upper()
            angle = (2 * math.pi * idx) / max(len(self._latest_devices), 1)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self._draw_node(mac, x, y, device)

        if self._pending_highlight:
            mac, status = self._pending_highlight
            self._pending_highlight = None
            self.highlight_device(mac, status)

    def _draw_backdrop(self) -> None:
        if not self.canvas:
            return
        self.canvas.delete("backdrop")
        width = max(self.canvas.winfo_width(), self._dimensions[0])
        height = max(self.canvas.winfo_height(), self._dimensions[1])
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2.8
        self.canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline=self.colors["text_secondary"],
            width=1,
            dash=(3, 3),
            tags="backdrop",
        )
        self.canvas.create_text(
            center_x,
            center_y,
            text="CYBRO CORE",
            fill=self.colors["text_secondary"],
            font=("Courier New", 10, "bold"),
            tags="backdrop",
        )

    def _draw_node(self, mac: str, x: float, y: float, device: dict) -> None:
        if not self.canvas:
            return
        node_radius = 18
        outline = self.colors["background"]
        node = self.canvas.create_oval(
            x - node_radius,
            y - node_radius,
            x + node_radius,
            y + node_radius,
            fill=self.colors["primary"],
            outline=outline,
            width=1,
            tags=("device", mac),
        )
        label = device.get("hostname") or device.get("vendor") or device.get("ip") or ""
        self.canvas.create_text(
            x,
            y + node_radius + 12,
            text=label[:18],
            fill=self.colors["text_secondary"],
            font=("Courier New", 8),
            tags=("device", f"{mac}-label"),
        )
        self.canvas.create_text(
            x,
            y - node_radius - 6,
            text=mac,
            fill=self.colors["background"],
            font=("Courier New", 7),
            tags=("device", f"{mac}-mac"),
        )
        self._device_nodes[mac] = node

    def _show_status(self, message: str, color: str) -> None:
        if not self.canvas:
            return
        if self._status_text:
            self.canvas.delete(self._status_text)
        self._status_text = self.canvas.create_text(
            10,
            10,
            anchor="w",
            fill=color,
            font=("Courier New", 9, "bold"),
            text=f"{datetime.now().strftime('%H:%M:%S')}  {message}",
        )

    def _status_color(self, status: str) -> str:
        lookup = {
            "NEW_DEVICE": self.colors["accent"],
            "DEVICE_REAPPEARED": "#4CAF50",
            "DEVICE_DISAPPEARED": "#F44336",
            "IP_CHANGED": "#FFC107",
        }
        return lookup.get(status, self.colors["primary"])
