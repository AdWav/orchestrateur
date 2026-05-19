from __future__ import annotations

from dataclasses import dataclass

from core.contracts import AgentDescriptor


@dataclass(frozen=True, slots=True)
class DevTeamPipeline:
    id: str
    name: str
    methodology: str
    step_ids: tuple[str, ...]
    purpose: str
    handoff_contracts: list[str]
    guardrails: list[str]
    role_descriptors: tuple[AgentDescriptor, ...]


TEAM_TDD = DevTeamPipeline(
    id="team-tdd",
    name="Equipe TDD",
    methodology="test-driven-development",
    step_ids=("write_tests", "code", "run_fix", "document"),
    purpose=(
        "Livrer une fonctionnalite en Test-Driven Development : tests d'abord, "
        "implementation minimale, execution avec corrections, puis documentation."
    ),
    handoff_contracts=[
        "write_tests -> code: cas de test, fixtures, criteres d'acceptation",
        "code -> run_fix: implementation, fichiers touches, commandes de test",
        "run_fix -> document: resultats d'execution, correctifs appliques, statut tests",
    ],
    guardrails=[
        "Les tests doivent etre ecrits avant le code de production.",
        "run_fix ne doit pas elargir le scope au-dela des tests existants.",
        "document resume le livrable et la preuve d'execution.",
    ],
    role_descriptors=(
        AgentDescriptor(
            role="write_tests",
            responsibility="Rediger les tests (unitaires/integration) avant toute implementation.",
            capabilities=["cas de test", "fixtures", "criteres d'acceptation", "pytest/jest"],
            allowed_inputs=["objectif", "contraintes", "criteres de succes", "spec fonctionnelle"],
            produces=["test_files", "acceptance_criteria", "test_plan"],
        ),
        AgentDescriptor(
            role="code",
            responsibility="Implementer le code minimal pour faire passer les tests.",
            capabilities=["implementation", "refactoring local", "respect du scope TDD"],
            allowed_inputs=["test_files", "handoff tests", "contraintes techniques"],
            produces=["source_files", "implementation_notes", "dependencies"],
        ),
        AgentDescriptor(
            role="run_fix",
            responsibility="Executer la suite de tests et corriger jusqu'a passage ou echec explicite.",
            capabilities=["execution tests", "diagnostic", "correctifs cibles"],
            allowed_inputs=["source_files", "test_files", "commandes de test"],
            produces=["test_run_report", "fixes_applied", "tests_passed"],
        ),
        AgentDescriptor(
            role="document",
            responsibility="Documenter le livrable, l'usage et les preuves d'execution.",
            capabilities=["README", "doc API", "changelog technique"],
            allowed_inputs=["implementation", "test_run_report", "criteres de succes"],
            produces=["documentation", "operator_notes", "delivery_summary"],
        ),
    ),
)

TEAM_CLASSIC = DevTeamPipeline(
    id="team-classic",
    name="Equipe Plan-Code-Test",
    methodology="plan-code-test-document",
    step_ids=("schematic", "code", "test_and_verify", "document"),
    purpose=(
        "Livrer une fonctionnalite en approche classique : schema et plan, "
        "implementation, creation et execution des tests, puis documentation."
    ),
    handoff_contracts=[
        "schematic -> code: diagramme, modules, interfaces, plan d'implementation",
        "code -> test_and_verify: sources, points d'extension, commandes de build",
        "test_and_verify -> document: rapport de tests, couverture, verdict",
    ],
    guardrails=[
        "schematic reste synthetique et actionnable pour le developpeur.",
        "test_and_verify cree les tests apres le code et exécute la suite.",
        "document ne doit pas contredire le verdict des tests.",
    ],
    role_descriptors=(
        AgentDescriptor(
            role="schematic",
            responsibility="Planifier et schematiser la solution (modules, flux, interfaces).",
            capabilities=["architecture legere", "diagrammes textuels", "decoupage modules"],
            allowed_inputs=["objectif", "contraintes", "contexte technique"],
            produces=["schematic", "module_plan", "implementation_order"],
        ),
        AgentDescriptor(
            role="code",
            responsibility="Coder la fonctionnalite selon le schema valide.",
            capabilities=["implementation", "patterns projet", "gestion des dependances"],
            allowed_inputs=["schematic", "module_plan", "contraintes"],
            produces=["source_files", "implementation_notes", "dependencies"],
        ),
        AgentDescriptor(
            role="test_and_verify",
            responsibility="Creer les tests puis executer et valider le comportement.",
            capabilities=["tests auto", "execution CI locale", "verdict qualite"],
            allowed_inputs=["source_files", "criteres de succes", "schematic"],
            produces=["test_files", "test_run_report", "tests_passed"],
        ),
        AgentDescriptor(
            role="document",
            responsibility="Documenter le livrable et les resultats de validation.",
            capabilities=["README", "doc API", "guide operateur"],
            allowed_inputs=["source_files", "test_run_report", "schematic"],
            produces=["documentation", "operator_notes", "delivery_summary"],
        ),
    ),
)

DEV_TEAM_PIPELINES: dict[str, DevTeamPipeline] = {
    TEAM_TDD.id: TEAM_TDD,
    TEAM_CLASSIC.id: TEAM_CLASSIC,
}

DEV_TEAM_BENCHMARK_ORDER: tuple[str, ...] = (TEAM_TDD.id, TEAM_CLASSIC.id)

DEV_PIPELINE_STEP_IDS: tuple[str, ...] = tuple(
    dict.fromkeys(step for team in DEV_TEAM_PIPELINES.values() for step in team.step_ids)
)

# Runners additionnels (catalogue / workflows enrichis) — union avec les pipelines ci-dessus.
EXTRA_DEV_RUNNER_STEP_IDS: tuple[str, ...] = (
    "code_backend",
    "code_frontend",
    "api_contract",
    "integration",
    "security",
    "review",
    "database",
    "devops",
)

ALL_DEV_RUNNER_STEP_IDS: tuple[str, ...] = tuple(
    dict.fromkeys([*DEV_PIPELINE_STEP_IDS, *EXTRA_DEV_RUNNER_STEP_IDS])
)
