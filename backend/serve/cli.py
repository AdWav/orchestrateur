from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

import httpx

from core.agent_gateway import LocalAgentGateway
from core.contracts import RepoAuditReport, RepoAuditRequest, TeamSpecification, WorkflowRun, WorkItem
from core.demo_scenarios import (
    DEMO_SCENARIOS,
    build_demo_business_story,
    build_demo_repo_audit_request,
    build_demo_specification_request,
)
from core.model_client import build_model_client_from_env
from core.catalog_bootstrap import ensure_dev_team_catalog
from core.catalog_factory import build_definition_catalog
from core.orchestrator import MultiAgentOrchestrator
from core.runtime_ollama_settings import RuntimeOllamaSettings


class OrchestratorClient:
    def __init__(self, api_url: str | None = None) -> None:
        self.api_url = api_url.rstrip("/") if api_url else None
        self._local_orchestrator: MultiAgentOrchestrator | None = None
        self._local_runtime_settings: RuntimeOllamaSettings | None = None

    @property
    def mode(self) -> str:
        return "remote-api" if self.api_url else "local"

    def _orchestrator(self) -> MultiAgentOrchestrator:
        if self._local_orchestrator is None:
            if self._local_runtime_settings is None:
                self._local_runtime_settings = RuntimeOllamaSettings.bootstrap_from_environment()
            gateway = LocalAgentGateway(
                model_client=build_model_client_from_env(self._local_runtime_settings),
            )
            catalog = build_definition_catalog()
            ensure_dev_team_catalog(catalog)
            self._local_orchestrator = MultiAgentOrchestrator(
                gateway=gateway,
                catalog=catalog,
            )
        return self._local_orchestrator

    def team_specification(self) -> TeamSpecification:
        if not self.api_url:
            return self._orchestrator().team_specification()
        response = httpx.get(f"{self.api_url}/team", timeout=30.0)
        response.raise_for_status()
        return TeamSpecification.model_validate(response.json())

    def run_specification(self, item: WorkItem) -> WorkflowRun:
        if not self.api_url:
            return self._orchestrator().run_specification_workflow(item)
        response = httpx.post(
            f"{self.api_url}/workflows/specification",
            json={
                "objective": item.objective,
                "context": _stringify_context(item.context),
                "constraints": item.constraints,
                "success_criteria": item.success_criteria,
                "use_case_id": item.use_case_id or "specification-factory",
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return WorkflowRun.model_validate(response.json())

    def run_repo_audit(self, request: RepoAuditRequest) -> RepoAuditReport:
        if not self.api_url:
            return self._orchestrator().run_repo_audit_workflow(request)
        response = httpx.post(
            f"{self.api_url}/workflows/repo-audit",
            json={
                "objective": request.objective,
                "repo_path": request.repo_target.root_path,
                "include_paths": request.audit_scope.include_paths,
                "exclude_paths": request.audit_scope.exclude_paths,
                "analysis_axes": request.audit_scope.analysis_axes,
                "read_limits": request.audit_scope.read_limits.model_dump(mode="json"),
                "constraints": request.constraints,
                "success_criteria": request.success_criteria,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return RepoAuditReport.model_validate(response.json())


def _stringify_context(context: dict[str, Any]) -> dict[str, str]:
    serialized: dict[str, str] = {}
    for key, value in context.items():
        if isinstance(value, str):
            serialized[str(key)] = value
            continue
        serialized[str(key)] = json.dumps(value, ensure_ascii=True)
    return serialized


def _parse_key_values(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Context entry '{raw}' must use the format key=value.")
        key, value = raw.split("=", 1)
        if not key:
            raise ValueError("Context entries must have a non-empty key.")
        parsed[key] = value
    return parsed


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrateur",
        description="CLI locale pour piloter les workflows de l'orchestrateur.",
    )
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--api-url",
        help="Base URL d'une API FastAPI existante. Sans cette option, la CLI execute le workflow localement.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("team", parents=[shared], help="Afficher la specification de l'equipe.")

    specification = subparsers.add_parser(
        "specification",
        parents=[shared],
        help="Executer le workflow de specification.",
    )
    specification.add_argument("--objective", required=True, help="Objectif principal du workflow.")
    specification.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Contexte additionnel, repetable.",
    )
    specification.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Contrainte du workflow, repetable.",
    )
    specification.add_argument(
        "--success-criterion",
        action="append",
        default=[],
        help="Critere de succes, repetable.",
    )
    specification.add_argument(
        "--use-case-id",
        default="specification-factory",
        help="Identifiant du cas d'usage cible.",
    )

    repo_audit = subparsers.add_parser(
        "repo-audit",
        parents=[shared],
        help="Executer l'audit lecture seule d'un depot.",
    )
    repo_audit.add_argument("--objective", required=True, help="Objectif de l'audit.")
    repo_audit.add_argument("--repo-path", default=".", help="Chemin du depot a analyser.")
    repo_audit.add_argument(
        "--analysis-axis",
        action="append",
        default=[],
        help="Axe d'analyse a couvrir, repetable.",
    )
    repo_audit.add_argument(
        "--include-path",
        action="append",
        default=[],
        help="Chemin a inclure explicitement, repetable.",
    )
    repo_audit.add_argument(
        "--exclude-path",
        action="append",
        default=[],
        help="Chemin a exclure explicitement, repetable.",
    )
    repo_audit.add_argument("--max-files", type=int, default=40, help="Nombre max de fichiers lus.")
    repo_audit.add_argument(
        "--max-bytes-per-file",
        type=int,
        default=12000,
        help="Nombre max d'octets lus par fichier.",
    )
    repo_audit.add_argument("--max-matches", type=int, default=40, help="Nombre max de matches recherches.")
    repo_audit.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Contrainte du workflow, repetable.",
    )
    repo_audit.add_argument(
        "--success-criterion",
        action="append",
        default=[],
        help="Critere de succes, repetable.",
    )

    demo = subparsers.add_parser(
        "demo",
        parents=[shared],
        help="Executer une demo complete sous forme de cellule projet d'entreprise.",
    )
    demo.add_argument("--repo-path", default=".", help="Depot cible pour la demonstration.")
    demo.add_argument(
        "--company-name",
        default="Atlas Conseil",
        help="Nom de l'organisation qui pilote la mission.",
    )
    demo.add_argument(
        "--client-name",
        default="Maison Orion",
        help="Nom du client, du dossier ou de la cible analysee.",
    )
    demo.add_argument(
        "--scenario",
        default="delivery-mission",
        choices=DEMO_SCENARIOS,
        help="Scenario metier utilise pour raconter la demo.",
    )

    return parser


def _team_payload(client: OrchestratorClient) -> dict[str, Any]:
    return client.team_specification().model_dump(mode="json")


def _specification_payload(client: OrchestratorClient, args: argparse.Namespace) -> dict[str, Any]:
    item = WorkItem(
        objective=args.objective,
        context=_parse_key_values(args.context),
        constraints=args.constraint,
        success_criteria=args.success_criterion,
        use_case_id=args.use_case_id,
    )
    return client.run_specification(item).model_dump(mode="json")


def _repo_audit_payload(client: OrchestratorClient, args: argparse.Namespace) -> dict[str, Any]:
    request = RepoAuditRequest(
        objective=args.objective,
        repo_target={"root_path": args.repo_path},
        audit_scope={
            "analysis_axes": args.analysis_axis or ["architecture", "tests", "docs", "security", "dependencies"],
            "include_paths": args.include_path,
            "exclude_paths": args.exclude_path,
            "read_limits": {
                "max_files": args.max_files,
                "max_bytes_per_file": args.max_bytes_per_file,
                "max_matches": args.max_matches,
            },
        },
        constraints=args.constraint,
        success_criteria=args.success_criterion,
    )
    return client.run_repo_audit(request).model_dump(mode="json")


def _demo_payload(client: OrchestratorClient, args: argparse.Namespace) -> dict[str, Any]:
    story = build_demo_business_story(
        scenario=args.scenario,
        company_name=args.company_name,
        client_name=args.client_name,
    )
    spec_request = build_demo_specification_request(
        scenario=args.scenario,
        company_name=args.company_name,
        client_name=args.client_name,
    )
    repo_request = build_demo_repo_audit_request(
        repo_path=args.repo_path,
        scenario=args.scenario,
        company_name=args.company_name,
        client_name=args.client_name,
    )
    return {
        "mode": client.mode,
        "api_url": client.api_url,
        "business_story": story,
        "team": client.team_specification().model_dump(mode="json"),
        "specification_request": spec_request.model_dump(mode="json"),
        "specification": client.run_specification(spec_request).model_dump(mode="json"),
        "repo_audit_request": repo_request.model_dump(mode="json"),
        "repo_audit": client.run_repo_audit(repo_request).model_dump(mode="json"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    client = OrchestratorClient(api_url=getattr(args, "api_url", None))
    handlers = {
        "team": lambda: _team_payload(client),
        "specification": lambda: _specification_payload(client, args),
        "repo-audit": lambda: _repo_audit_payload(client, args),
        "demo": lambda: _demo_payload(client, args),
    }
    try:
        payload = handlers[args.command]()
    except ValueError as exc:
        parser.error(str(exc))
    except httpx.HTTPError as exc:
        parser.exit(status=1, message=f"HTTP error: {exc}\n")
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
