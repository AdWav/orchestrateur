from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from core.contracts import AgentDefinition, WorkflowDefinition


class DefinitionCatalog(Protocol):
    def list_agents(self) -> list[AgentDefinition]: ...

    def get_agent(self, agent_id: str) -> AgentDefinition: ...

    def save_agent(self, definition: AgentDefinition, overwrite: bool = False) -> AgentDefinition: ...

    def list_workflows(self) -> list[WorkflowDefinition]: ...

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition: ...

    def save_workflow(
        self,
        definition: WorkflowDefinition,
        overwrite: bool = False,
    ) -> WorkflowDefinition: ...


class FileDefinitionCatalog:
    def __init__(self, root_path: str | Path | None = None) -> None:
        if root_path is None:
            root_path = os.getenv("ORCHESTRATOR_CATALOG_ROOT")
        if root_path is None:
            root_path = Path(__file__).resolve().parents[2] / "catalog"
        self.root_path = Path(root_path)
        self.agents_path = self.root_path / "agents"
        self.workflows_path = self.root_path / "workflows"

    def list_agents(self) -> list[AgentDefinition]:
        return sorted(
            (AgentDefinition.model_validate(self._read_json(path)) for path in self._iter_json_files(self.agents_path)),
            key=lambda definition: definition.id,
        )

    def get_agent(self, agent_id: str) -> AgentDefinition:
        path = self.agents_path / f"{agent_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown agent definition '{agent_id}'.")
        return AgentDefinition.model_validate(self._read_json(path))

    def save_agent(self, definition: AgentDefinition, overwrite: bool = False) -> AgentDefinition:
        self.agents_path.mkdir(parents=True, exist_ok=True)
        path = self.agents_path / f"{definition.id}.json"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Agent definition '{definition.id}' already exists.")
        self._write_json(path, definition.model_dump(mode="json"))
        return definition

    def list_workflows(self) -> list[WorkflowDefinition]:
        return sorted(
            (
                WorkflowDefinition.model_validate(self._read_json(path))
                for path in self._iter_json_files(self.workflows_path)
            ),
            key=lambda definition: definition.id,
        )

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        path = self.workflows_path / f"{workflow_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown workflow definition '{workflow_id}'.")
        return WorkflowDefinition.model_validate(self._read_json(path))

    def save_workflow(
        self,
        definition: WorkflowDefinition,
        overwrite: bool = False,
    ) -> WorkflowDefinition:
        self.workflows_path.mkdir(parents=True, exist_ok=True)
        path = self.workflows_path / f"{definition.id}.json"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Workflow definition '{definition.id}' already exists.")

        known_agents = {agent.id for agent in self.list_agents()}
        unknown_agents = sorted(
            {
                step.agent_definition_id
                for step in definition.steps
                if step.agent_definition_id not in known_agents
            }
        )
        if unknown_agents:
            unknown = ", ".join(unknown_agents)
            raise ValueError(f"Workflow definition references unknown agents: {unknown}.")

        self._write_json(path, definition.model_dump(mode="json"))
        return definition

    def _iter_json_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(path for path in directory.glob("*.json") if path.is_file())

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
