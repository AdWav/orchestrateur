from __future__ import annotations

import os
from urllib.parse import urlparse


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def build_role_urls() -> dict[str, str]:
    return {
        "plan": _env("PLANNER_AGENT_URL", "http://planner-agent:8001"),
        "research": _env("RESEARCHER_AGENT_URL", "http://researcher-agent:8002"),
        "execute": _env("EXECUTOR_AGENT_URL", "http://executor-agent:8003"),
        "verify": _env("VERIFIER_AGENT_URL", "http://verifier-agent:8004"),
    }


def ollama_base_url() -> str:
    default = "http://ollama:11434" if running_in_compose() else "http://localhost:11434"
    return _env("OLLAMA_BASE_URL", default)


def database_url() -> str | None:
    value = os.getenv("DATABASE_URL", "").strip()
    return value or None


def catalog_backend() -> str:
    return _env("CATALOG_BACKEND", "file").lower()


def port_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.port:
        return str(parsed.port)
    if parsed.scheme == "https":
        return "443"
    if parsed.scheme == "http":
        return "80"
    return None


def ui_allowed_origins() -> list[str]:
    configured = os.getenv("UI_ALLOWED_ORIGINS")
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        if origins:
            return origins

    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8100",
        "http://127.0.0.1:8100",
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost",
        "http://127.0.0.1",
    ]
    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    if frontend_url and frontend_url not in defaults:
        defaults.append(frontend_url)
    return defaults


def running_in_compose() -> bool:
    return _env("ORCHESTRATOR_MODE", "local").lower() == "compose"
