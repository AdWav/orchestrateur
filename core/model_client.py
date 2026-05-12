from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol

import httpx

from core.runtime_ollama_settings import RuntimeOllamaSettings


@dataclass(slots=True)
class ModelResponse:
    content: str
    backend: str = "dry-run"


class ModelClient(Protocol):
    def generate(self, role: str, prompt: str) -> ModelResponse:
        ...


class DryRunModelClient:
    def generate(self, role: str, prompt: str) -> ModelResponse:
        snippet = prompt.strip().replace("\n", " ")
        compact = snippet[:180]
        return ModelResponse(
            content=f"{role} synthesized a draft from: {compact}",
            backend="dry-run",
        )


class OllamaModelClient:
    def __init__(
        self,
        base_url: str,
        runtime: RuntimeOllamaSettings,
        timeout_seconds: float = 120.0,
        temperature: float = 0.2,
        num_predict: int = 96,
        keep_alive: str = "5m",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.runtime = runtime
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.num_predict = num_predict
        self.keep_alive = keep_alive

    def model_for_role(self, role: str) -> str:
        return self.runtime.model_for_runner(role)

    def generate(self, role: str, prompt: str) -> ModelResponse:
        model = self.model_for_role(role)
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.num_predict,
                },
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("response", "").strip()
        if not content:
            raise RuntimeError(f"Ollama returned an empty response for model '{model}'.")
        return ModelResponse(content=content, backend=f"ollama:{model}")


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def build_model_client_from_env(runtime: RuntimeOllamaSettings) -> ModelClient:
    backend = _env("MODEL_BACKEND", "dry-run").lower()
    if backend != "ollama":
        return DryRunModelClient()

    return OllamaModelClient(
        base_url=_env("OLLAMA_BASE_URL", "http://ollama:11434"),
        runtime=runtime,
        timeout_seconds=float(_env("OLLAMA_TIMEOUT_SECONDS", "120")),
        temperature=float(_env("OLLAMA_TEMPERATURE", "0.2")),
        num_predict=int(_env("OLLAMA_NUM_PREDICT", "96")),
        keep_alive=_env("OLLAMA_KEEP_ALIVE", "5m"),
    )
