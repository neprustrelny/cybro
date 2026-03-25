from __future__ import annotations

from typing import Dict, Any, List


COGNITIVE_BIASES = {
    "confirmation": ["sure", "certain", "obvious", "self-evident"],
    "anchoring": ["first impression", "initial data"],
    "optimism": ["cannot fail", "guaranteed"],
}


def detect_biases(decision: Dict[str, Any], feedback: str) -> List[str]:
    """Naive keyword-based bias detection."""
    text = f"{decision} {feedback}".lower()
    detected = []
    for bias, keywords in COGNITIVE_BIASES.items():
        if any(keyword in text for keyword in keywords):
            detected.append(bias)
    return detected
