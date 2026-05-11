from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol

import httpx


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
        default_model: str,
        role_models: dict[str, str] | None = None,
        timeout_seconds: float = 120.0,
        temperature: float = 0.2,
        num_predict: int = 96,
        keep_alive: str = "5m",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.role_models = role_models or {}
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.num_predict = num_predict
        self.keep_alive = keep_alive

    def model_for_role(self, role: str) -> str:
        return self.role_models.get(role, self.default_model)

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


def _role_model_env(role: str, default_model: str) -> str:
    env_name = f"OLLAMA_MODEL_{role.upper()}"
    return _env(env_name, default_model)


def build_model_client_from_env() -> ModelClient:
    backend = _env("MODEL_BACKEND", "dry-run").lower()
    if backend != "ollama":
        return DryRunModelClient()

    default_model = _env("OLLAMA_DEFAULT_MODEL", "qwen2.5:0.5b")
    role_models = {
        "Planner": _role_model_env("planner", default_model),
        "Researcher": _role_model_env("researcher", default_model),
        "Executor": _role_model_env("executor", default_model),
        "Verifier": _role_model_env("verifier", default_model),
    }
    return OllamaModelClient(
        base_url=_env("OLLAMA_BASE_URL", "http://ollama:11434"),
        default_model=default_model,
        role_models=role_models,
        timeout_seconds=float(_env("OLLAMA_TIMEOUT_SECONDS", "120")),
        temperature=float(_env("OLLAMA_TEMPERATURE", "0.2")),
        num_predict=int(_env("OLLAMA_NUM_PREDICT", "96")),
        keep_alive=_env("OLLAMA_KEEP_ALIVE", "5m"),
    )
