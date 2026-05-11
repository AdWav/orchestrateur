from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from core.agent_runtime import ROLE_CLASS_MAP, run_agent_request
from core.contracts import AgentExecutionRequest, AgentExecutionResponse
from core.model_client import build_model_client_from_env

ROLE_NAME = os.getenv("AGENT_ROLE", "Planner")
SERVICE_PORT = os.getenv("SERVICE_PORT", "8001")
MODEL_CLIENT = build_model_client_from_env()

app = FastAPI(
    title=f"{ROLE_NAME} Agent Service",
    version="0.1.0",
    description="Service HTTP dedie a un role specialise dans le mesh Docker.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "role": ROLE_NAME,
        "service_port": SERVICE_PORT,
        "model_backend": MODEL_CLIENT.__class__.__name__,
    }


@app.post("/v1/agent/run", response_model=AgentExecutionResponse)
def run_role(request: AgentExecutionRequest) -> AgentExecutionResponse:
    if ROLE_NAME not in ROLE_CLASS_MAP:
        raise HTTPException(status_code=500, detail=f"Unsupported AGENT_ROLE '{ROLE_NAME}'")
    if request.role != ROLE_NAME:
        raise HTTPException(
            status_code=400,
            detail=f"Service configured for role '{ROLE_NAME}', received '{request.role}'",
        )
    try:
        return run_agent_request(request, model_client=MODEL_CLIENT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
