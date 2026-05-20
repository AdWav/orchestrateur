from __future__ import annotations

import os

from app.models.api_schemas import ChatTurn, SamplingPreviewRequest
from app.services.sampling_preview_context import (
    build_ollama_messages,
    clip_chat_history,
    resolve_preview_live_context,
)


def test_clip_chat_history_respects_cap(monkeypatch) -> None:
    monkeypatch.setenv("JOURNEY_MAX_HISTORY_MESSAGES", "2")
    history = [
        ChatTurn(role="user", content="a"),
        ChatTurn(role="assistant", content="b"),
        ChatTurn(role="user", content="c"),
    ]
    clipped = clip_chat_history(history)
    assert len(clipped) == 2
    assert clipped[0].content == "b"


def test_build_ollama_messages_appends_current_prompt() -> None:
    history = [ChatTurn(role="user", content="Hi"), ChatTurn(role="assistant", content="Hello")]
    msgs = build_ollama_messages(history, "Next?")
    assert msgs[-1] == {"role": "user", "content": "Next?"}
    assert len(msgs) == 3


def test_resolve_preview_live_context_chat_mode(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "test-model")

    class _Ollama:
        def default_model(self) -> str:
            return "test-model"

    class _Sampling:
        def live_snapshot(self):
            from core.sampling_settings import SamplingSnapshot

            return SamplingSnapshot()

    monkeypatch.setattr(
        "app.services.runtime_context.get_runtime_ollama",
        lambda: _Ollama(),
    )
    monkeypatch.setattr(
        "app.services.runtime_context.get_runtime_sampling",
        lambda: _Sampling(),
    )
    monkeypatch.setattr(
        "app.services.ollama_ops.validate_models_installed",
        lambda _names: None,
    )

    payload = SamplingPreviewRequest(
        prompt="suite",
        history=[ChatTurn(role="user", content="debut")],
    )
    ctx = resolve_preview_live_context(payload)
    assert ctx.mode == "chat"
    assert ctx.messages is not None
    assert ctx.history_message_count == 1
    assert ctx.messages[-1]["content"] == "suite"
