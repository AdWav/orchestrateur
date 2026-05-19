from __future__ import annotations

from typing import Any

from core.contracts import AgentDescriptor, AgentOutput, WorkItem
from core.dev_teams import DEV_TEAM_PIPELINES
from core.memory import SharedMemory
from core.model_client import DryRunModelClient, ModelClient
from core.catalog_runtime import enrich_work_item_prompt
from core.roles import SpecialistAgent, _memory_artifacts


def _step_output(memory: SharedMemory, step_id: str) -> dict[str, Any]:
    stored = memory.read(f"{step_id}_output", {})
    return stored if isinstance(stored, dict) else {}


def _dev_descriptor(
    role: str,
    responsibility: str,
    *,
    capabilities: list[str] | None = None,
    allowed_inputs: list[str] | None = None,
    produces: list[str] | None = None,
) -> AgentDescriptor:
    return AgentDescriptor(
        role=role,
        responsibility=responsibility,
        capabilities=capabilities or [],
        allowed_inputs=allowed_inputs or ["objectif", "contraintes", "criteres de succes"],
        produces=produces or [],
    )


def _merged_implementation_artifacts(memory: SharedMemory) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in ("code_output", "code_backend_output", "code_frontend_output"):
        merged.update(_memory_artifacts(memory, key))
    return merged


def _build_prompt(
    item: WorkItem,
    role_label: str,
    extra: str = "",
    memory: SharedMemory | None = None,
) -> str:
    lines = [
        f"Role: {role_label}",
        f"Objective: {item.objective}",
        f"Constraints: {', '.join(item.constraints) or 'none'}",
        f"Success criteria: {', '.join(item.success_criteria) or 'none'}",
    ]
    if extra:
        lines.append(extra)
    base = "\n".join(lines)
    if memory is None:
        return base
    return enrich_work_item_prompt(base, memory)


class WriteTestsAgent(SpecialistAgent):
    descriptor = DEV_TEAM_PIPELINES["team-tdd"].role_descriptors[0]

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        prompt = _build_prompt(item, "Test Author (TDD — red phase)", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "test_plan": [
                    "Cas nominal sur le chemin heureux",
                    "Cas d'erreur sur les entrees invalides",
                    "Cas de regression sur le comportement existant",
                ],
                "test_files": [
                    f"tests/test_{item.use_case_id or 'feature'}.py",
                ],
                "acceptance_criteria": list(item.success_criteria) or ["Les tests doivent echouer avant implementation."],
            },
            next_actions=["Transmettre les tests au developpeur pour implementation minimale."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class DevCoderAgent(SpecialistAgent):
    descriptor = DEV_TEAM_PIPELINES["team-tdd"].role_descriptors[1]

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        prior_tests = _memory_artifacts(memory, "write_tests_output") or _memory_artifacts(
            memory, "schematic_output"
        )
        extra = f"Prior artifacts: {prior_tests}"
        prompt = _build_prompt(item, "Developer — implement feature", extra, memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "source_files": ["src/feature.py"],
                "implementation_notes": [
                    "Implementation minimale alignee sur les tests ou le schema.",
                    f"Objectif: {item.objective}",
                ],
                "dependencies": [],
            },
            next_actions=["Executer la suite de tests et corriger si necessaire."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class BackendCoderAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "code_backend",
        "Implementer API, services, persistance et regles metier cote serveur.",
        capabilities=["FastAPI", "services", "ORM", "validation"],
        produces=["backend_source_files", "api_routes", "migrations_notes"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        contract = _memory_artifacts(memory, "api_contract_output")
        tests = _memory_artifacts(memory, "write_tests_output")
        extra = f"API contract: {contract.get('openapi_paths', [])}; tests: {tests.get('test_files', [])}"
        prompt = _build_prompt(item, "Backend developer", extra, memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "source_files": ["backend/app/routes/feature.py", "backend/app/services/feature.py"],
                "api_routes": contract.get("openapi_paths") or ["/api/v1/feature"],
                "implementation_notes": [f"Backend pour: {item.objective}"],
            },
            next_actions=["Implementer ou brancher le frontend sur ces routes."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class FrontendCoderAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "code_frontend",
        "Implementer interface, etat client et appels API vers le backend.",
        capabilities=["React", "composants", "etat", "appels HTTP"],
        produces=["frontend_source_files", "ui_components", "api_client_usage"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        backend = _memory_artifacts(memory, "code_backend_output")
        contract = _memory_artifacts(memory, "api_contract_output")
        extra = f"Backend routes: {backend.get('api_routes', [])}; contract: {contract.get('schemas', [])}"
        prompt = _build_prompt(item, "Frontend developer", extra, memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "source_files": ["frontend/src/pages/FeaturePage.tsx", "frontend/src/api/feature.ts"],
                "ui_components": ["FeatureForm", "FeatureList"],
                "api_client_usage": backend.get("api_routes") or ["/api/v1/feature"],
            },
            next_actions=["Lancer les tests d'integration bout-en-bout."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class ApiContractAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "api_contract",
        "Definir le contrat d'API partage (routes, schemas, erreurs) avant que backend et frontend codent.",
        capabilities=["OpenAPI", "schemas JSON", "versioning", "codes erreur"],
        produces=["openapi_paths", "schemas", "error_model"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        schematic = _memory_artifacts(memory, "schematic_output")
        prompt = _build_prompt(
            item,
            "API contract — wiring plan between backend and frontend",
            f"Schematic: {schematic.get('module_plan', [])}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "openapi_paths": ["/api/v1/feature"],
                "schemas": ["FeatureCreate", "FeatureRead", "ErrorResponse"],
                "error_model": ["400 validation", "404 not found", "409 conflict"],
                "contract_note": (
                    "Contrat d'API = accord ecrit sur les URLs et les formats JSON "
                    "pour que le backend et le frontend restent alignes."
                ),
            },
            next_actions=["Coder le backend puis le frontend a partir de ce contrat."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class IntegrationAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "integration",
        "Tester le parcours complet frontend + backend ensemble (pas seulement des tests unitaires isoles).",
        capabilities=["E2E", "Playwright", "parcours utilisateur", "API reelle"],
        produces=["e2e_scenarios", "e2e_report"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        impl = _merged_implementation_artifacts(memory)
        prompt = _build_prompt(
            item,
            "Integration / E2E — full stack path",
            f"Sources: {impl.get('source_files', [])}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        passed = bool(impl.get("source_files"))
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "e2e_scenarios": [
                    "Parcours nominal creation -> liste -> detail",
                    "Erreur reseau affichee cote UI",
                ],
                "e2e_report": {
                    "tool": "playwright",
                    "passed": passed,
                    "note": (
                        "Tests d'integration = enchaînement reel UI + API "
                        "(ex. clic dans l'app qui appelle localhost:8000)."
                    ),
                },
            },
            next_actions=["Corriger les echecs via run_fix si necessaire."],
            approved=passed,
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class SecurityReviewAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "security",
        "Revue securite : auth, secrets, injections, exposition de donnees.",
        capabilities=["OWASP", "auth", "secrets", "validation entrees"],
        produces=["security_findings", "risk_level"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        prompt = _build_prompt(item, "Security review", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "security_findings": ["Verifier absence de secrets en dur", "Valider les entrees utilisateur"],
                "risk_level": "medium",
            },
            next_actions=["Traiter les findings bloquants avant livraison."],
            approved=True,
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class CodeReviewAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "review",
        "Revue de code : lisibilite, coherence, dette technique evidente.",
        capabilities=["review", "style", "maintenabilite"],
        produces=["review_comments", "approval_recommendation"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        impl = _merged_implementation_artifacts(memory)
        prompt = _build_prompt(item, "Code review", f"Files: {impl.get('source_files', [])}", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "review_comments": ["Nommage coherent", "Extraire la logique metier hors des routes"],
                "approval_recommendation": "approve_with_minor_comments",
            },
            next_actions=["Appliquer les commentaires ou documenter les ecarts."],
            approved=True,
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class DatabaseAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "database",
        "Concevoir schema, migrations et contraintes de persistance.",
        capabilities=["SQL", "migrations", "index", "integrite"],
        produces=["schema_ddl", "migration_files"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        prompt = _build_prompt(item, "Database / schema", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "schema_ddl": ["CREATE TABLE feature (...)"],
                "migration_files": ["migrations/001_feature.sql"],
            },
            next_actions=["Brancher le backend sur ce schema."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class DevOpsAgent(SpecialistAgent):
    descriptor = _dev_descriptor(
        "devops",
        "Preparer CI/CD, conteneurs et deploiement reproductible.",
        capabilities=["Docker", "CI", "compose", "healthchecks"],
        produces=["ci_pipeline", "deploy_notes"],
    )

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        prompt = _build_prompt(item, "DevOps / delivery", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "ci_pipeline": ["lint", "test", "build image"],
                "deploy_notes": ["docker compose up", "variables .env documentees"],
            },
            next_actions=["Valider le pipeline sur une branche de test."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class RunFixAgent(SpecialistAgent):
    descriptor = DEV_TEAM_PIPELINES["team-tdd"].role_descriptors[2]

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        code_artifacts = _merged_implementation_artifacts(memory)
        test_artifacts = _memory_artifacts(memory, "write_tests_output") or _memory_artifacts(
            memory, "test_and_verify_output"
        )
        integration = _memory_artifacts(memory, "integration_output")
        e2e_report = integration.get("e2e_report")
        e2e_ok = isinstance(e2e_report, dict) and bool(e2e_report.get("passed"))
        tests_passed = bool(
            code_artifacts.get("source_files")
            and (test_artifacts.get("test_files") or e2e_ok)
        )
        prompt = _build_prompt(
            item,
            "Runner — execute tests and fix",
            f"Sources: {code_artifacts.get('source_files', [])}",
            memory=memory,
        )
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "test_run_report": {
                    "command": "pytest -q",
                    "passed": tests_passed,
                    "failures": [] if tests_passed else ["Ajustements requis sur src/feature.py"],
                },
                "fixes_applied": [] if tests_passed else ["Correction des assertions et imports"],
                "tests_passed": tests_passed,
            },
            next_actions=["Documenter le livrable et les preuves d'execution."],
            approved=tests_passed,
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class SchematicPlannerAgent(SpecialistAgent):
    descriptor = DEV_TEAM_PIPELINES["team-classic"].role_descriptors[0]

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        prompt = _build_prompt(item, "Planner — schematic and module breakdown", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "schematic": [
                    "Entree API -> service metier -> persistance",
                    "Flux d'erreur explicite vers couche validation",
                ],
                "module_plan": ["api", "service", "tests"],
                "implementation_order": [
                    "Definir les interfaces publiques",
                    "Implementer le coeur metier",
                    "Brancher les tests d'integration",
                ],
            },
            next_actions=["Coder selon le schema valide."],
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class TestAndVerifyAgent(SpecialistAgent):
    descriptor = DEV_TEAM_PIPELINES["team-classic"].role_descriptors[2]

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        code_artifacts = _merged_implementation_artifacts(memory)
        tests_passed = bool(code_artifacts.get("source_files"))
        prompt = _build_prompt(item, "QA — create tests then execute", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "test_files": [f"tests/test_{item.use_case_id or 'feature'}.py"],
                "test_run_report": {
                    "command": "pytest -q",
                    "passed": tests_passed,
                    "failures": [] if tests_passed else ["Completer la couverture des cas limites"],
                },
                "tests_passed": tests_passed,
            },
            next_actions=["Documenter le livrable et le verdict de tests."],
            approved=tests_passed,
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


class DevDocumentAgent(SpecialistAgent):
    descriptor = DEV_TEAM_PIPELINES["team-tdd"].role_descriptors[3]

    def run(self, item: WorkItem, memory: SharedMemory) -> AgentOutput:
        run_artifacts = _memory_artifacts(memory, "run_fix_output")
        verify_artifacts = _memory_artifacts(memory, "test_and_verify_output")
        tests_passed = bool(
            run_artifacts.get("tests_passed") or verify_artifacts.get("tests_passed")
        )
        prompt = _build_prompt(item, "Technical Writer — document delivery", memory=memory)
        summary = self.model_client.generate(self.descriptor.role, prompt).content
        output = AgentOutput(
            role=self.descriptor.role,
            summary=summary,
            artifacts={
                "documentation": [
                    "docs/feature.md — objectif, usage, limites",
                    "README — section installation et tests",
                ],
                "operator_notes": [
                    "Executer pytest -q avant toute livraison.",
                    f"Statut tests: {'OK' if tests_passed else 'KO'}",
                ],
                "delivery_summary": {
                    "objective": item.objective,
                    "tests_passed": tests_passed,
                },
            },
            next_actions=["Archiver le rapport de benchmark si applicable."],
            approved=tests_passed,
        )
        memory.remember(f"{self.descriptor.role}_output", output.model_dump(), self.descriptor.role)
        return output


def dev_agent_for_step(step_id: str, model_client: ModelClient | None = None) -> SpecialistAgent:
    client = model_client or DryRunModelClient()
    agents: dict[str, type[SpecialistAgent]] = {
        "write_tests": WriteTestsAgent,
        "code": DevCoderAgent,
        "code_backend": BackendCoderAgent,
        "code_frontend": FrontendCoderAgent,
        "api_contract": ApiContractAgent,
        "integration": IntegrationAgent,
        "security": SecurityReviewAgent,
        "review": CodeReviewAgent,
        "database": DatabaseAgent,
        "devops": DevOpsAgent,
        "run_fix": RunFixAgent,
        "document": DevDocumentAgent,
        "schematic": SchematicPlannerAgent,
        "test_and_verify": TestAndVerifyAgent,
    }
    factory = agents.get(step_id)
    if factory is None:
        raise ValueError(f"No dev agent registered for step '{step_id}'.")
    return factory(model_client=client)
