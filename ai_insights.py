"""
Post-processing helpers for CYBRO WatchDog AI insights.
"""

from __future__ import annotations

from typing import Any, Dict
import json
import re

DEFAULT_INSIGHT = {
    "risk": "low",
    "classification": "unknown",
    "explanation": "No AI analysis available",
    "recommended_action": "monitor",
}

VALID_RISKS = {"low", "medium", "high"}
VALID_CLASSIFICATIONS = {"mobile", "pc", "iot", "unknown"}
VALID_ACTIONS = {"monitor", "alert", "ignore"}


def normalize_insight(ai_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize the AI response into the expected schema.

    Returns DEFAULT_INSIGHT if parsing fails.
    """
    if not ai_response:
        return DEFAULT_INSIGHT.copy()

    text = ai_response.get("response")
    if not text:
        return DEFAULT_INSIGHT.copy()

    parsed = _extract_json(text)
    if not isinstance(parsed, dict):
        return DEFAULT_INSIGHT.copy()

    risk = str(parsed.get("risk", "low")).lower()
    classification = str(parsed.get("classification", "unknown")).lower()
    explanation = str(parsed.get("explanation", DEFAULT_INSIGHT["explanation"]))[:400]
    action = str(parsed.get("recommended_action", "monitor")).lower()

    if risk not in VALID_RISKS:
        risk = "low"
    if classification not in VALID_CLASSIFICATIONS:
        classification = "unknown"
    if action not in VALID_ACTIONS:
        action = "monitor"

    return {
        "risk": risk,
        "classification": classification,
        "explanation": explanation,
        "recommended_action": action,
    }


def _extract_json(text: str) -> Dict[str, Any]:
    """Attempt to parse JSON from the response text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    snippet = match.group(0)
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return {}

