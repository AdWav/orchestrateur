from __future__ import annotations

from threading import Lock
from typing import Any


class SharedMemory:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._events: list[dict[str, Any]] = []
        self._lock = Lock()

    def remember(self, key: str, value: Any, role: str) -> None:
        with self._lock:
            self._state[key] = value
            self._events.append({"type": "remember", "role": role, "key": key})

    def append_event(
        self,
        role: str,
        message: str,
        data: dict[str, Any] | None = None,
        event_type: str = "event",
    ) -> None:
        with self._lock:
            event = {"type": event_type, "role": role, "message": message}
            if data:
                event["data"] = data
            self._events.append(event)

    def read(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": dict(self._state),
                "events": list(self._events),
            }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> "SharedMemory":
        memory = cls()
        memory._state = dict(snapshot.get("state", {}))
        memory._events = list(snapshot.get("events", []))
        return memory
