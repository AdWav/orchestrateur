from __future__ import annotations

PIPELINE_STEP_IDS: tuple[str, ...] = ("plan", "research", "execute", "verify")

LEGACY_ENGINE_ROLE_BY_STEP_ID: dict[str, str] = {
    "plan": "Planner",
    "research": "Researcher",
    "execute": "Executor",
    "verify": "Verifier",
}

STEP_ID_BY_LEGACY_ENGINE_ROLE: dict[str, str] = {
    legacy: sid for sid, legacy in LEGACY_ENGINE_ROLE_BY_STEP_ID.items()
}
