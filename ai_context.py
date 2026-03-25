"""
Prompt/context builder for the CYBRO WatchDog AI analyst.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

try:
    from event_engine import DeviceEvent
    from device_registry import DeviceRegistry
except Exception:  # pragma: no cover - used at runtime
    DeviceEvent = Any  # type: ignore
    DeviceRegistry = Any  # type: ignore


def build_context(
    event: DeviceEvent, registry: Optional[DeviceRegistry] = None
) -> Dict[str, Any]:
    """Create a compact context dict describing the device and event."""
    payload = event.payload or {}
    registry_snapshot: Dict[str, Any] = {}

    device_record = None
    if registry and hasattr(registry, "devices"):
        device_record = registry.devices.get(event.mac)

    if device_record:
        registry_snapshot = {
            "first_seen": device_record.first_seen.isoformat(),
            "last_seen": device_record.last_seen.isoformat(),
            "seen_count": device_record.seen_count,
            "ip_history": device_record.ip_history,
            "hostnames": sorted(device_record.hostnames),
            "vendor": device_record.vendor,
        }

    context = {
        "event_type": getattr(event.event_type, "value", str(event.event_type)),
        "mac": event.mac,
        "timestamp": event.timestamp.isoformat(),
        "ip": payload.get("ip") or payload.get("new_ip") or registry_snapshot.get("ip_history", [None])[0],
        "hostname": payload.get("hostname")
        or (payload.get("hostnames")[0] if payload.get("hostnames") else None),
        "vendor": payload.get("vendor") or registry_snapshot.get("vendor"),
        "ip_history": payload.get("ip_history")
        or registry_snapshot.get("ip_history", []),
        "hostnames": payload.get("hostnames") or registry_snapshot.get("hostnames", []),
        "seen_count": registry_snapshot.get("seen_count", 1),
        "protocols": payload.get("protocols", []),
        "recommended_focus": _derive_focus(event),
    }

    context["registry_snapshot"] = registry_snapshot
    return context


def build_prompt(context: Dict[str, Any]) -> str:
    """Convert the context into a deterministic prompt for the AI model."""
    safe_context = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    instruction = (
        "You are CYBRO WatchDog's passive network analyst. "
        "Given the structured context, determine the probable device type, "
        "risk, and recommended operator action. Focus on unusual presence, "
        "vendor reputation, hostname clues, and IP churn. "
        "Respond ONLY with compact JSON using keys "
        '["risk","classification","explanation","recommended_action"]. '
        "risk must be one of: low, medium, high. "
        "classification must be one of: mobile, pc, iot, unknown. "
        "recommended_action must be one of: monitor, alert, ignore."
    )
    return f"{instruction}\nCONTEXT:{safe_context}\nOUTPUT_JSON:"


def _derive_focus(event: DeviceEvent) -> str:
    """Provide a lightweight hint about what the AI should pay attention to."""
    evt = getattr(event.event_type, "value", str(event.event_type)).upper()
    if "IP_CHANGE" in evt:
        return "Evaluate risk of IP churn or spoofing."
    if "REAPPEARED" in evt:
        return "Device went silent and came back; assess persistence."
    if "NEW_DEVICE" in evt:
        return "New device on LAN; evaluate trustworthiness."
    return "General device context."

