"""Application ASGI MCP (FastMCP + Streamable HTTP) reliant l'API FastAPI Orchestrateur."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route


def _api_base() -> str:
    return os.environ.get("ORCHESTRATOR_API_BASE", "http://localhost:8000").rstrip("/")


def _timeout_seconds() -> float:
    return float(os.environ.get("ORCHESTRATOR_HTTP_TIMEOUT_SECONDS", "600"))


def _env_flag(name: str, default_true: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default_true
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _is_mcp_streamable_path(path_without_query: str) -> bool:
    """True si la cible correspond a l endpoint Streamable HTTP du SDK MCP (suffix `/mcp`)."""
    p = path_without_query.rstrip("/")
    return len(p) >= 4 and p.endswith("/mcp")


def _accept_media_primaries(accept_header: str) -> list[str]:
    parts: list[str] = []
    for chunk in accept_header.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        primary = chunk.split(";", maxsplit=1)[0].strip()
        parts.append(primary)
    return parts


def _merge_accept_required(accept_header: str, *, method_upper: str, json_only_posts: bool) -> str | None:
    """Retourne un nouvel en-tête Accept ou None si deja conforme."""

    primaries = _accept_media_primaries(accept_header)
    need_sse = method_upper == "GET"
    need_json = method_upper == "POST" and json_only_posts

    has_sse = any(p.startswith("text/event-stream") for p in primaries)
    has_json = any(
        p.startswith("application/json")
        or p.startswith("application/*")
        or p == "*/*"
        for p in primaries
    )

    extras: list[str] = []
    if need_sse and not has_sse:
        extras.append("text/event-stream")
    if need_json and not has_json:
        extras.append("application/json")
    if not extras:
        return None

    base = ", ".join(p.strip() for p in accept_header.split(",") if p.strip())
    if base:
        return f"{base}, {', '.join(extras)}"
    return ", ".join(extras)


class MCPStreamableAcceptCompatMiddleware(BaseHTTPMiddleware):
    """Le transport MCP exige des types `Accept` precis ; plusieurs clients oublient SSE sur GET."""

    def __init__(self, app, *, enabled: bool, json_only_posts: bool) -> None:
        super().__init__(app)
        self._enabled = enabled
        self._json_posts = json_only_posts

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if not self._enabled or not _is_mcp_streamable_path(request.url.path.split("?", 1)[0]):
            return await call_next(request)

        augmented = _merge_accept_required(
            request.headers.get("accept", ""),
            method_upper=request.method.upper(),
            json_only_posts=self._json_posts,
        )
        if augmented is None:
            return await call_next(request)

        scope = dict(request.scope)
        rebuilt: list[tuple[bytes, bytes]] = []
        replaced = False
        accept_key = b"accept"
        new_val_bytes = augmented.encode("latin1")
        for key_b, val_b in scope["headers"]:
            lowered = key_b.lower()
            if lowered == accept_key:
                rebuilt.append((key_b, new_val_bytes))
                replaced = True
            else:
                rebuilt.append((key_b, val_b))
        if not replaced:
            rebuilt.append((accept_key, new_val_bytes))
        scope["headers"] = rebuilt
        request = Request(scope, request.receive)
        return await call_next(request)


_RELAX_ACCEPT = _env_flag("MCP_RELAX_ACCEPT_HEADERS", True)

mcp = FastMCP(
    "Orchestrateur",
    instructions=(
        "Outils MCP pour l'API Orchestrateur local : catalogue (agents, workflows), "
        "sante du mesh, execution de workflows du catalogue et benchmark dev-team."
    ),
    stateless_http=True,
    json_response=True,
)


async def _request(
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
) -> dict | list:
    timeout = httpx.Timeout(_timeout_seconds())
    async with httpx.AsyncClient(base_url=_api_base(), timeout=timeout) as client:
        response = await client.request(method, path, json=json_body)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def orchestrateur_health() -> str:
    """Verifie que l'API Orchestrateur repond (GET /health)."""
    try:
        data = await _request("GET", "/health")
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001 — retour textuel pour le modele
        return json.dumps(
            {"error": str(exc), "orchestrator_api_base": _api_base()},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
async def orchestrateur_services_status() -> str:
    """Recupere l'etat des services connus par le backend (GET /services/status)."""
    try:
        data = await _request("GET", "/services/status")
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"error": str(exc), "orchestrator_api_base": _api_base()},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
async def list_catalog_agents() -> str:
    """Liste les definitions d'agents du catalogue (GET /definitions/agents)."""
    try:
        data = await _request("GET", "/definitions/agents")
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"error": str(exc), "orchestrator_api_base": _api_base()},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
async def list_catalog_workflows() -> str:
    """Liste les definitions de workflows du catalogue (GET /definitions/workflows)."""
    try:
        data = await _request("GET", "/definitions/workflows")
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"error": str(exc), "orchestrator_api_base": _api_base()},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
async def run_catalog_workflow(
    workflow_id: str,
    objective: str,
    context_json: str = "{}",
    constraints_json: str = "[]",
    success_criteria_json: str = "[]",
    use_case_id: str | None = None,
) -> str:
    """Execute un workflow du catalogue (POST /workflows/catalog/{workflow_id}).

    Parametres JSON : context_json (objet), constraints_json et success_criteria_json (tableaux JSON).
    """
    try:
        context = json.loads(context_json or "{}")
        constraints = json.loads(constraints_json or "[]")
        success_criteria = json.loads(success_criteria_json or "[]")
        body: dict = {
            "objective": objective,
            "context": context,
            "constraints": constraints,
            "success_criteria": success_criteria,
        }
        if use_case_id:
            body["use_case_id"] = use_case_id
        path = f"/workflows/catalog/{workflow_id}"
        data = await _request("POST", path, json_body=body)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"JSON invalide: {exc}"}, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"error": str(exc), "orchestrator_api_base": _api_base()},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
async def run_dev_team_benchmark(
    objective: str,
    context_json: str = "{}",
    constraints_json: str | None = None,
    success_criteria_json: str | None = None,
    team_order_json: str = '["team-tdd", "team-classic"]',
    materialize_workspace: bool = True,
) -> str:
    """Lance le benchmark comparatif TDD vs classique (POST /workflows/dev-team-benchmark)."""
    try:
        context = json.loads(context_json or "{}")
        body: dict = {
            "objective": objective,
            "context": context,
            "materialize_workspace": materialize_workspace,
        }
        if constraints_json is not None:
            body["constraints"] = json.loads(constraints_json)
        if success_criteria_json is not None:
            body["success_criteria"] = json.loads(success_criteria_json)
        body["team_order"] = json.loads(team_order_json or '["team-tdd", "team-classic"]')
        data = await _request("POST", "/workflows/dev-team-benchmark", json_body=body)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"JSON invalide: {exc}"}, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"error": str(exc), "orchestrator_api_base": _api_base()},
            ensure_ascii=False,
            indent=2,
        )


@asynccontextmanager
async def _lifespan(_: Starlette) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        yield


async def _healthz(_request: Request) -> JSONResponse:
    """Probe Docker / LB ; hors protocole MCP (ne depend pas des en-tetes Accept)."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "orchestrateur-mcp",
            "mcp_streamable_http": "/mcp",
            "notes": (
                "Connectez les clients MCP distants via Streamable HTTP sur /mcp ; "
                "pour Cursor en local, preferez le transport stdio (python -m orchestrateur_mcp)."
            ),
        }
    )


_inner_mcp_http = mcp.streamable_http_app()

app = Starlette(
    routes=[
        Route("/healthz", _healthz, methods=["GET"]),
        Mount("/", app=_inner_mcp_http),
    ],
    lifespan=_lifespan,
)
app.add_middleware(
    MCPStreamableAcceptCompatMiddleware,
    enabled=_RELAX_ACCEPT,
    json_only_posts=True,
)
