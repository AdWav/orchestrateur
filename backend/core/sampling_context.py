from __future__ import annotations

from typing import Any, Callable

_orchestration_provider: Callable[[], dict[str, Any]] | None = None
_live_provider: Callable[[], dict[str, Any]] | None = None


def attach_orchestration_sampling_provider(provider: Callable[[], dict[str, Any]]) -> None:
    global _orchestration_provider
    _orchestration_provider = provider


def attach_live_sampling_provider(provider: Callable[[], dict[str, Any]]) -> None:
    global _live_provider
    _live_provider = provider


def orchestration_sampling_options() -> dict[str, Any]:
    if _orchestration_provider is None:
        return {}
    return _orchestration_provider()


def live_sampling_options() -> dict[str, Any]:
    if _live_provider is None:
        return {}
    return _live_provider()
