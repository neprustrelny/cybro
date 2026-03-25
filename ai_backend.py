from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Dict, List
from urllib.parse import urlparse

import requests


Message = Dict[str, str]


class BaseBackend(ABC):
    name = "base"

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: List[Message], timeout: int = 60) -> str:
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> str:
        raise NotImplementedError


class LocalOllamaBackend(BaseBackend):
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = os.getenv("CYBRO_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self._model_from_env = bool(os.getenv("CYBRO_OLLAMA_MODEL"))
        self.model = os.getenv("CYBRO_OLLAMA_MODEL", "llama3:latest")
        self._status = ""
        self._policy_status = ""

    def describe(self) -> str:
        return f"url={self.base_url}, model={self.model}"

    def status(self) -> str:
        if self._status:
            return self._status
        if self._policy_status:
            return self._policy_status
        return "unknown"

    def mark_local_only_policy(self) -> None:
        self._policy_status = "blocked: local-only mode"

    def _enforce_local_endpoint(self) -> None:
        hostname = (urlparse(self.base_url).hostname or "").lower()
        if hostname not in {"localhost", "127.0.0.1"}:
            self._status = "blocked: non-local endpoint"
            raise RuntimeError(self._status)

    def _resolve_default_model(self, names: set[str]) -> None:
        if self.model in names:
            return
        if self._model_from_env:
            return
        for candidate in ("llama3:latest", "llama3.2:latest"):
            if candidate in names:
                self.model = candidate
                return

    def is_available(self) -> bool:
        try:
            self._enforce_local_endpoint()
        except RuntimeError:
            return False

        tags_url = f"{self.base_url}/api/tags"
        try:
            resp = requests.get(tags_url, timeout=4)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            self._status = f"Ollama unavailable: {exc}"
            return False

        models = payload.get("models") or []
        names = {(m.get("name") or m.get("model")) for m in models}
        self._resolve_default_model(names)
        if self.model in names:
            self._status = "ready"
            return True

        self._status = f"model '{self.model}' not found"
        return False

    def chat(self, messages: List[Message], timeout: int = 300) -> str:
        """Robustná verzia: /api/chat → fallback na /api/generate pre llama3.2"""
        self._enforce_local_endpoint()
        chat_url = f"{self.base_url}/api/chat"
        payload_chat = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_predict": 512,
            }
        }
        try:
            resp = requests.post(chat_url, json=payload_chat, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                content = ((data.get("message") or {}).get("content") or "").strip()
                if content:
                    return content
        except:
            pass  # fallback

        # FALLBACK na /api/generate (funguje vždy na llama3.2)
        gen_url = f"{self.base_url}/api/generate"
        prompt = "\n".join([f"{m.get('role','user').upper()}: {m.get('content','')}" for m in messages])
        payload_gen = {
            "model": self.model,
            "prompt": prompt + "\nASSISTANT:",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_predict": 512,
            },
        }
        resp = requests.post(gen_url, json=payload_gen, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = (data.get("response") or "").strip()
        if not content:
            raise RuntimeError("Empty response from both /api/chat and /api/generate")
        return content

    def _chat_generate_fallback(self, messages: List[Message], timeout: int = 60) -> str:
        gen_url = f"{self.base_url}/api/generate"
        prompt = _messages_to_prompt(messages)
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        resp = requests.post(gen_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = (data.get("response") or "").strip()
        if not content:
            raise RuntimeError("Empty response from Ollama /api/generate.")
        return content


class OpenAIBackend(BaseBackend):
    name = "openai-disabled"

    def __init__(self) -> None:
        self._status = "blocked: local-only mode"

    def describe(self) -> str:
        return "disabled"

    def status(self) -> str:
        return self._status

    def is_available(self) -> bool:
        return False

    def chat(self, messages: List[Message], timeout: int = 60) -> str:
        raise RuntimeError(self._status)


def get_backend() -> BaseBackend:
    selected = os.getenv("CYBRO_AI_BACKEND", "").strip().lower()
    has_openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
    backend = LocalOllamaBackend()
    if selected == "openai" or has_openai_key:
        backend.mark_local_only_policy()
    return backend


def _messages_to_prompt(messages: List[Message]) -> str:
    parts: List[str] = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)
