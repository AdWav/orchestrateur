from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import get_container
from core.contracts import TeamSpecification, UseCaseDefinition

router = APIRouter(tags=["team"])


@router.get("/use-cases", response_model=list[UseCaseDefinition])
def list_use_cases() -> list[UseCaseDefinition]:
    return get_container().team_controller.list_use_cases()


@router.get("/teams", response_model=list[TeamSpecification])
def list_teams() -> list[TeamSpecification]:
    return get_container().team_controller.list_team_specifications()


@router.get("/team", response_model=TeamSpecification)
def team_specification(
    team_id: str | None = Query(default=None, description="ID equipe (ex. team-tdd, team-classic)"),
) -> TeamSpecification:
    return get_container().team_controller.team_specification(team_id)
