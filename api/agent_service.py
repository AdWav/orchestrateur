from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from core.agent_runtime import STEP_RUNNER_CLASS_MAP, run_agent_request
from core.contracts import AgentExecutionRequest, AgentExecutionResponse
from core.model_client import build_model_client_from_env
from core.pipeline import STEP_ID_BY_LEGACY_ENGINE_ROLE
from core.runtime_ollama_settings import RuntimeOllamaSettings

_raw_agent_role = os.getenv("AGENT_ROLE", "plan")
SERVICE_RUNNER_STEP = STEP_ID_BY_LEGACY_ENGINE_ROLE.get(_raw_agent_role, _raw_agent_role)
SERVICE_PORT = os.getenv("SERVICE_PORT", "8001")

if SERVICE_RUNNER_STEP not in STEP_RUNNER_CLASS_MAP:
    raise RuntimeError(
        f"AGENT_ROLE '{_raw_agent_role}' resout en '{SERVICE_RUNNER_STEP}' "
        f"qui n'est pas une etape connue: {sorted(STEP_RUNNER_CLASS_MAP)}."
    )

_runtime = RuntimeOllamaSettings.bootstrap_from_environment()
MODEL_CLIENT = build_model_client_from_env(_runtime)

app = FastAPI(
    title=f"{SERVICE_RUNNER_STEP} Agent Service",
    version="0.1.0",
    description="Service HTTP dedie a une etape du pipeline dans le mesh Docker.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "role": SERVICE_RUNNER_STEP,
        "service_port": SERVICE_PORT,
        "model_backend": MODEL_CLIENT.__class__.__name__,
    }


@app.post("/agent/run", response_model=AgentExecutionResponse)
def run_role(request: AgentExecutionRequest) -> AgentExecutionResponse:
    if request.role != SERVICE_RUNNER_STEP:
        raise HTTPException(
            status_code=400,
            detail=f"Service configured for runner '{SERVICE_RUNNER_STEP}', received '{request.role}'",
        )
    try:
        return run_agent_request(request, model_client=MODEL_CLIENT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
