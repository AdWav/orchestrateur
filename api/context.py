from __future__ import annotations

from core.runtime_ollama_settings import RuntimeOllamaSettings

_runtime_ollama: RuntimeOllamaSettings | None = None


def attach_runtime_ollama(settings: RuntimeOllamaSettings) -> None:
    global _runtime_ollama
    _runtime_ollama = settings


def get_runtime_ollama() -> RuntimeOllamaSettings:
    assert _runtime_ollama is not None, "attach_runtime_ollama must run before accessing settings"
    return _runtime_ollama
