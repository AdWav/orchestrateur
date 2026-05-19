from __future__ import annotations

from core.runtime_ollama_settings import RuntimeOllamaSettings
from core.sampling_settings import RuntimeSamplingSettings

_runtime_ollama: RuntimeOllamaSettings | None = None
_runtime_sampling: RuntimeSamplingSettings | None = None


def attach_runtime_ollama(settings: RuntimeOllamaSettings) -> None:
    global _runtime_ollama
    _runtime_ollama = settings


def get_runtime_ollama() -> RuntimeOllamaSettings:
    assert _runtime_ollama is not None, "attach_runtime_ollama must run before accessing settings"
    return _runtime_ollama


def attach_runtime_sampling(settings: RuntimeSamplingSettings) -> None:
    global _runtime_sampling
    _runtime_sampling = settings


def get_runtime_sampling() -> RuntimeSamplingSettings:
    assert _runtime_sampling is not None, "attach_runtime_sampling must run before accessing settings"
    return _runtime_sampling
