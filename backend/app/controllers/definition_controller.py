from __future__ import annotations

from core.contracts import AgentDefinition, WorkflowDefinition
from core.definition_catalog import DefinitionCatalog


class DefinitionController:
    def __init__(self, catalog: DefinitionCatalog) -> None:
        self._catalog = catalog

    def list_agents(self) -> list[AgentDefinition]:
        return self._catalog.list_agents()

    def create_agent(self, definition: AgentDefinition) -> AgentDefinition:
        return self._catalog.save_agent(definition)

    def list_workflows(self) -> list[WorkflowDefinition]:
        return self._catalog.list_workflows()

    def create_workflow(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        return self._catalog.save_workflow(definition)
