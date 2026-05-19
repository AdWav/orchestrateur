from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import build_role_urls, database_url, ollama_base_url, port_from_url, running_in_compose
from app.models.api_schemas import ServiceMeshStatusResponse, ServiceStatus


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


def _base_services() -> list[ServiceStatus]:
    return [
        ServiceStatus(
            key="po",
            label="API",
            target="http://localhost:8000",
            port="8000",
            active=True,
        ),
        ServiceStatus(
            key="sampling",
            label="Sampling",
            target="in-process",
            active=True,
        ),
    ]


def _internal_role_services() -> list[ServiceStatus]:
    return [
        ServiceStatus(key="plan", label="plan", target="in-process", active=True),
        ServiceStatus(key="research", label="research", target="in-process", active=True),
        ServiceStatus(key="execute", label="execute", target="in-process", active=True),
        ServiceStatus(key="verify", label="verify", target="in-process", active=True),
    ]


def collect_service_status() -> ServiceMeshStatusResponse:
    services = _base_services()

    if running_in_compose():
        urls = build_role_urls()
        targets = [
            ProbeTarget(key="plan", label="plan", url=urls["plan"], health_path="/health"),
            ProbeTarget(
                key="research",
                label="research",
                url=urls["research"],
                health_path="/health",
            ),
            ProbeTarget(
                key="execute",
                label="execute",
                url=urls["execute"],
                health_path="/health",
            ),
            ProbeTarget(key="verify", label="verify", url=urls["verify"], health_path="/health"),
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
    else:
        services.extend(_internal_role_services())

    runtime_url = ollama_base_url()
    services.append(
        ServiceStatus(
            key="ollama",
            label="Ollama",
            target=runtime_url,
            port=port_from_url(runtime_url),
            active=_probe(runtime_url, "/api/tags"),
        )
    )

    db_url = database_url()
    if db_url:
        services.append(
            ServiceStatus(
                key="mariadb",
                label="MariaDB",
                target=db_url.split("@")[-1] if "@" in db_url else db_url,
                port="3306",
                active=True,
            )
        )

    return ServiceMeshStatusResponse(services=services)
