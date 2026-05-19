from __future__ import annotations

from core.contracts import TeamSpecification, UseCaseDefinition
from core.orchestrator import MultiAgentOrchestrator
from core.use_cases import USE_CASES


class TeamController:
    def __init__(self, orchestrator: MultiAgentOrchestrator) -> None:
        self._orchestrator = orchestrator

    def list_use_cases(self) -> list[UseCaseDefinition]:
        return USE_CASES

    def team_specification(self, team_id: str | None = None) -> TeamSpecification:
        return self._orchestrator.team_specification(team_id)

    def list_team_specifications(self) -> list[TeamSpecification]:
        return self._orchestrator.list_team_specifications()
