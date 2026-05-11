from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def build_role_urls() -> dict[str, str]:
    return {
        "Planner": _env("PLANNER_AGENT_URL", "http://planner-agent:8001"),
        "Researcher": _env("RESEARCHER_AGENT_URL", "http://researcher-agent:8002"),
        "Executor": _env("EXECUTOR_AGENT_URL", "http://executor-agent:8003"),
        "Verifier": _env("VERIFIER_AGENT_URL", "http://verifier-agent:8004"),
    }


def running_in_compose() -> bool:
    return _env("ORCHESTRATOR_MODE", "local").lower() == "compose"
