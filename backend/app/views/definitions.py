from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.dependencies import get_container
from core.contracts import AgentDefinition, WorkflowDefinition

router = APIRouter(prefix="/definitions", tags=["definitions"])


@router.get("/agents", response_model=list[AgentDefinition])
def list_agent_definitions() -> list[AgentDefinition]:
    return get_container().definition_controller.list_agents()


@router.post("/agents", response_model=AgentDefinition, status_code=status.HTTP_201_CREATED)
def create_agent_definition(definition: AgentDefinition) -> AgentDefinition:
    try:
        return get_container().definition_controller.create_agent(definition)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workflows", response_model=list[WorkflowDefinition])
def list_workflow_definitions() -> list[WorkflowDefinition]:
    return get_container().definition_controller.list_workflows()


@router.post("/workflows", response_model=WorkflowDefinition, status_code=status.HTTP_201_CREATED)
def create_workflow_definition(definition: WorkflowDefinition) -> WorkflowDefinition:
    try:
        return get_container().definition_controller.create_workflow(definition)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
