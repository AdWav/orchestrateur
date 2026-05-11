from __future__ import annotations

from dataclasses import dataclass

import httpx

from api.schemas import ServiceMeshStatusResponse, ServiceStatus
from api.settings import build_role_urls, ollama_base_url, port_from_url


@dataclass(frozen=True, slots=True)
class ProbeTarget:
    key: str
    label: str
    url: str
    health_path: str


def _probe(url: str, health_path: str) -> bool:
    try:
        response = httpx.get(f"{url.rstrip('/')}{health_path}", timeout=1.5)
    except httpx.HTTPError:
        return False
    return response.is_success


def collect_service_status() -> ServiceMeshStatusResponse:
    services = [
        ServiceStatus(
            key="po",
            label="PO",
            target="http://localhost:8000",
            port="8000",
            active=True,
        )
    ]

    targets = [
        ProbeTarget(key="planner", label="Planner", url=build_role_urls()["Planner"], health_path="/health"),
        ProbeTarget(
            key="researcher",
            label="Researcher",
            url=build_role_urls()["Researcher"],
            health_path="/health",
        ),
        ProbeTarget(key="executor", label="Executor", url=build_role_urls()["Executor"], health_path="/health"),
        ProbeTarget(key="verifier", label="Verifier", url=build_role_urls()["Verifier"], health_path="/health"),
        ProbeTarget(key="ollama", label="Ollama", url=ollama_base_url(), health_path="/api/tags"),
    ]

    for target in targets:
        services.append(
            ServiceStatus(
                key=target.key,
                label=target.label,
                target=target.url,
                port=port_from_url(target.url),
                active=_probe(target.url, target.health_path),
            )
        )

    return ServiceMeshStatusResponse(services=services)
