from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from core.agent_runtime import run_agent_request
from core.contracts import AgentExecutionRequest, AgentOutput, WorkItem


class AgentGateway(ABC):
    @abstractmethod
    def run_agent(
        self,
        role: str,
        work_item: WorkItem,
        memory: dict[str, object],
    ) -> tuple[AgentOutput, dict[str, object]]:
        raise NotImplementedError


class LocalAgentGateway(AgentGateway):
    def run_agent(
        self,
        role: str,
        work_item: WorkItem,
        memory: dict[str, object],
    ) -> tuple[AgentOutput, dict[str, object]]:
        response = run_agent_request(
            AgentExecutionRequest(role=role, work_item=work_item, memory=memory)
        )
        return response.output, response.memory


class HttpAgentGateway(AgentGateway):
    def __init__(
        self,
        role_urls: dict[str, str],
        timeout_seconds: float = 30.0,
    ) -> None:
        self.role_urls = role_urls
        self.timeout_seconds = timeout_seconds

    def run_agent(
        self,
        role: str,
        work_item: WorkItem,
        memory: dict[str, object],
    ) -> tuple[AgentOutput, dict[str, object]]:
        base_url = self.role_urls.get(role)
        if not base_url:
            known_roles = ", ".join(sorted(self.role_urls))
            raise ValueError(f"No service URL configured for role '{role}'. Known roles: {known_roles}")

        payload = AgentExecutionRequest(role=role, work_item=work_item, memory=memory)
        response = httpx.post(
            f"{base_url.rstrip('/')}/v1/agent/run",
            json=payload.model_dump(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        parsed = response.json()
        return AgentOutput.model_validate(parsed["output"]), parsed["memory"]
