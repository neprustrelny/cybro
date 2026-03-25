"""
Local AI engine wrapper for CYBRO WatchDog.

Uses the Ollama HTTP API (localhost) to evaluate passive network events.
"""

from __future__ import annotations

from typing import Any, Dict
import json
import logging

import requests

LOGGER = logging.getLogger("cybro.ai_engine")
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
MODEL_NAME = "marek-ai:latest"


def analyze_event(context: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
    """
    Submit the prepared prompt to Ollama and return its response.

    Args:
        context: Dictionary containing at least the key "prompt".
        timeout: HTTP timeout in seconds.

    Returns:
        Dict with the key "response" when successful, otherwise empty dict.
    """
    prompt = context.get("prompt")
    if not prompt:
        return {}

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "repeat_penalty": 1.1,
        },
    }

    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL, json=payload, timeout=timeout  # type: ignore[call-arg]
        )
        resp.raise_for_status()
    except Exception as exc:
        LOGGER.debug("AI request failed: %s", exc)
        return {}

    try:
        data = resp.json()
    except json.JSONDecodeError:
        LOGGER.debug("Invalid AI response JSON")
        return {}

    response_text = data.get("response")
    if not response_text:
        return {}
    return {"response": response_text, "model": data.get("model", MODEL_NAME)}


def is_model_available(timeout: int = 3) -> bool:
    """Check whether the configured model is available in Ollama."""
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=timeout)  # type: ignore[call-arg]
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        LOGGER.debug("AI availability check failed: %s", exc)
        return False

    models = data.get("models") or []
    for model in models:
        name = model.get("name") or model.get("model")
        if name == MODEL_NAME:
            return True
    LOGGER.debug("Model %s not found in Ollama tags", MODEL_NAME)
    return False
