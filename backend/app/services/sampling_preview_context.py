from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from app.models.api_schemas import ChatTurn, SamplingPreviewRequest


@dataclass(frozen=True)
class PreviewLiveContext:
    model: str
    prompt: str
    live_options: dict[str, Any]
    num_predict: int
    mode: Literal["generate", "chat"]
    messages: list[dict[str, str]] | None = None
    history_message_count: int = 0
    history_char_count: int = 0


def _max_history_messages() -> int:
    return max(0, int(os.getenv("JOURNEY_MAX_HISTORY_MESSAGES", "40")))


def clip_chat_history(history: list[ChatTurn]) -> list[ChatTurn]:
    cap = _max_history_messages()
    if cap <= 0 or len(history) <= cap:
        return history
    return history[-cap:]


def build_ollama_messages(history: list[ChatTurn], prompt: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for turn in history:
        content = turn.content.strip()
        if not content:
            continue
        rows.append({"role": turn.role, "content": content})
    rows.append({"role": "user", "content": prompt.strip()})
    return rows


def history_char_count(history: list[ChatTurn]) -> int:
    return sum(len(t.content) for t in history)


def resolve_preview_live_context(payload: SamplingPreviewRequest) -> PreviewLiveContext:
    from app.services import ollama_ops
    from app.services.runtime_context import get_runtime_ollama, get_runtime_sampling

    model = (payload.model or "").strip() or get_runtime_ollama().default_model()
    if not model:
        raise ValueError("Aucun modele par defaut configure.")
    ollama_ops.validate_models_installed({model})

    prompt = payload.prompt.strip()
    if not prompt:
        raise ValueError("Le prompt ne peut pas etre vide.")

    live_options = get_runtime_sampling().live_snapshot().to_ollama_options()
    num_predict = int(live_options.pop("num_predict", None) or 96)

    clipped = clip_chat_history(list(payload.history))
    if clipped:
        messages = build_ollama_messages(clipped, prompt)
        return PreviewLiveContext(
            model=model,
            prompt=prompt,
            live_options=live_options,
            num_predict=num_predict,
            mode="chat",
            messages=messages,
            history_message_count=len(clipped),
            history_char_count=history_char_count(clipped),
        )

    return PreviewLiveContext(
        model=model,
        prompt=prompt,
        live_options=live_options,
        num_predict=num_predict,
        mode="generate",
        messages=None,
        history_message_count=0,
        history_char_count=0,
    )


def extract_stream_token(chunk: dict[str, Any], *, mode: Literal["generate", "chat"]) -> str | None:
    if mode == "chat":
        message = chunk.get("message")
        if isinstance(message, dict):
            token = message.get("content")
            return token if isinstance(token, str) and token else None
        return None
    token = chunk.get("response")
    return token if isinstance(token, str) and token else None


def extract_final_content(chunk: dict[str, Any], *, mode: Literal["generate", "chat"]) -> str:
    if mode == "chat":
        message = chunk.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
        return ""
    content = chunk.get("response")
    return content.strip() if isinstance(content, str) else ""
