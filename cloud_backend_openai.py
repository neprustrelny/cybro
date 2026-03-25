import json
import os

import requests


def send_openai_responses(payload_text: str, model: str, timeout: int = 60) -> str:
    api_key = os.getenv("CYBRO_OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing CYBRO_OPENAI_API_KEY")
    if len(payload_text) > 50_000:
        raise RuntimeError("Cloud payload too large")

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "CYBRO/1.0",
    }
    body = {
        "model": model,
        "input": payload_text,
    }

    def collect_strings(node):
        found = []
        if isinstance(node, str):
            stripped = node.strip()
            if stripped:
                found.append(stripped)
            return found
        if isinstance(node, list):
            for item in node:
                found.extend(collect_strings(item))
            return found
        if isinstance(node, dict):
            preferred_keys = ("output_text", "text", "content")
            for key in preferred_keys:
                if key in node:
                    found.extend(collect_strings(node[key]))
            for key, value in node.items():
                if key not in preferred_keys:
                    found.extend(collect_strings(value))
            return found
        return found

    try:
        response = requests.post(url, headers=headers, json=body, timeout=timeout)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict):
            if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
                return payload["output_text"].strip()

            output = payload.get("output")
            if output is not None:
                texts = collect_strings(output)
                if texts:
                    return "\n".join(texts).strip()

            texts = collect_strings(payload)
            if texts:
                return "\n".join(texts).strip()

        pretty = json.dumps(payload, ensure_ascii=False, indent=2)
        return pretty[:4000]
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Cloud API error: {exc}") from exc
