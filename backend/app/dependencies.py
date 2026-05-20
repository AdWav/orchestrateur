from __future__ import annotations

from dataclasses import dataclass

from app.controllers.builder_controller import BuilderController
from app.controllers.definition_controller import DefinitionController
from app.controllers.ollama_runtime_controller import OllamaRuntimeController
from app.controllers.sampling_controller import SamplingController
from app.controllers.team_controller import TeamController
from app.controllers.workflow_controller import WorkflowController
from app.services.runtime_context import attach_runtime_ollama, attach_runtime_sampling
from core.sampling_context import attach_live_sampling_provider, attach_orchestration_sampling_provider
from core.sampling_settings import RuntimeSamplingSettings
from core.agent_gateway import HybridAgentGateway, LocalAgentGateway
from core.catalog_factory import build_definition_catalog
from core.definition_catalog import DefinitionCatalog
from core.model_client import build_model_client_from_env
from core.catalog_bootstrap import ensure_dev_team_catalog
from core.orchestrator import MultiAgentOrchestrator
from core.runtime_ollama_settings import RuntimeOllamaSettings
from app.config.settings import build_role_urls, running_in_compose


@dataclass(slots=True)
class AppContainer:
    orchestrator: MultiAgentOrchestrator
    catalog: DefinitionCatalog
    definition_controller: DefinitionController
    workflow_controller: WorkflowController
    team_controller: TeamController
    ollama_runtime_controller: OllamaRuntimeController
    sampling_controller: SamplingController
    builder_controller: BuilderController


_container: AppContainer | None = None


def init_container() -> AppContainer:
    global _container
    runtime_settings = RuntimeOllamaSettings.bootstrap_from_environment()
    attach_runtime_ollama(runtime_settings)
    sampling_settings = RuntimeSamplingSettings.bootstrap_from_environment()
    attach_runtime_sampling(sampling_settings)
    attach_orchestration_sampling_provider(
        lambda: sampling_settings.orchestration_snapshot().to_ollama_options(),
    )
    attach_live_sampling_provider(
        lambda: sampling_settings.live_snapshot().to_ollama_options(),
    )

    local_client = build_model_client_from_env(runtime_settings)
    gateway = (
        HybridAgentGateway(build_role_urls(), model_client=local_client)
        if running_in_compose()
        else LocalAgentGateway(model_client=local_client)
    )
    catalog = build_definition_catalog()
    ensure_dev_team_catalog(catalog)
    orchestrator = MultiAgentOrchestrator(gateway=gateway, catalog=catalog)

    _container = AppContainer(
        orchestrator=orchestrator,
        catalog=catalog,
        definition_controller=DefinitionController(catalog),
        workflow_controller=WorkflowController(orchestrator),
        team_controller=TeamController(orchestrator),
        ollama_runtime_controller=OllamaRuntimeController(),
        sampling_controller=SamplingController(),
        builder_controller=BuilderController(),
    )
    return _container


def get_container() -> AppContainer:
    if _container is None:
        return init_container()
    return _container


def reset_container() -> None:
    global _container
    _container = None
