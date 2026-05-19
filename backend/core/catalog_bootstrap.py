from __future__ import annotations

from core.contracts import AgentDefinition, WorkflowDefinition, WorkflowStepDefinition
from core.definition_catalog import DefinitionCatalog

DEV_TEAM_AGENT_PRESETS: list[AgentDefinition] = [
    AgentDefinition(
        id="schematic",
        name="Schema et plan",
        business_role="Schematic / plan",
        mission="Planifier et schematiser la solution (modules, flux, interfaces) avant implementation.",
        runner_role="schematic",
        capabilities=["architecture legere", "diagrammes textuels", "decoupage modules"],
        inputs=["objectif", "contraintes", "contexte technique"],
        outputs=["schematic", "module_plan", "implementation_order"],
        guardrails=["Rester synthetique et actionnable pour le developpeur."],
    ),
    AgentDefinition(
        id="api_contract",
        name="Contrat d'API",
        business_role="Contrat d'API",
        mission=(
            "Produire le contrat d'API partage : routes, schemas JSON et erreurs. "
            "C'est le plan de cablage entre backend et frontend pour qu'ils codent la meme chose."
        ),
        runner_role="api_contract",
        capabilities=["OpenAPI", "schemas", "versioning", "codes erreur"],
        inputs=["schematic", "objectif"],
        outputs=["openapi_paths", "schemas", "error_model"],
        guardrails=["Pas d'implementation : uniquement le contrat."],
    ),
    AgentDefinition(
        id="code",
        name="Implementation (generique)",
        business_role="Developer",
        mission="Implementer le code minimal lorsque la stack n'est pas scindee backend/frontend.",
        runner_role="code",
        capabilities=["implementation", "refactoring local"],
        inputs=["schematic", "tests", "contraintes techniques"],
        outputs=["source_files", "implementation_notes"],
        guardrails=["Preferer code_backend + code_frontend si la feature est full stack."],
    ),
    AgentDefinition(
        id="code_backend",
        name="Code backend",
        business_role="Backend developer",
        mission="Implementer API, services, persistance et regles metier cote serveur.",
        runner_role="code_backend",
        capabilities=["FastAPI", "services", "ORM", "validation"],
        inputs=["api_contract", "tests", "schematic"],
        outputs=["backend_source_files", "api_routes"],
        guardrails=["Respecter le contrat d'API si present."],
    ),
    AgentDefinition(
        id="code_frontend",
        name="Code frontend",
        business_role="Frontend developer",
        mission="Implementer l'interface, l'etat client et les appels vers l'API backend.",
        runner_role="code_frontend",
        capabilities=["React", "composants", "etat", "fetch API"],
        inputs=["api_contract", "code_backend", "maquettes"],
        outputs=["frontend_source_files", "ui_components"],
        guardrails=["Consommer les routes definies dans le contrat d'API."],
    ),
    AgentDefinition(
        id="database",
        name="Base de donnees",
        business_role="Database",
        mission="Definir schema, migrations SQL et contraintes d'integrite.",
        runner_role="database",
        capabilities=["SQL", "migrations", "index"],
        inputs=["schematic", "api_contract"],
        outputs=["schema_ddl", "migration_files"],
        guardrails=["Aligner le schema avec le contrat d'API."],
    ),
    AgentDefinition(
        id="write_tests",
        name="Tests d'abord",
        business_role="Test author",
        mission="Rediger les tests et criteres d'acceptation avant toute implementation (TDD).",
        runner_role="write_tests",
        capabilities=["cas de test", "pytest", "criteres d'acceptation"],
        inputs=["objectif", "contraintes", "criteres de succes"],
        outputs=["test_files", "acceptance_criteria", "test_plan"],
        guardrails=["Les tests doivent refleter les criteres de succes du workflow."],
    ),
    AgentDefinition(
        id="test_and_verify",
        name="Tests unitaires / integration locale",
        business_role="QA",
        mission="Creer les tests puis executer et valider le comportement apres implementation (souvent par couche).",
        runner_role="test_and_verify",
        capabilities=["tests auto", "pytest", "verdict qualite"],
        inputs=["source_files", "criteres de succes"],
        outputs=["test_files", "test_run_report", "tests_passed"],
        guardrails=["Le verdict doit etre explicite avant documentation."],
    ),
    AgentDefinition(
        id="integration",
        name="Tests bout-en-bout",
        business_role="Integration / E2E",
        mission=(
            "Verifier le parcours complet utilisateur : l'UI appelle le vrai backend "
            "(ex. Playwright + API locale). Pas seulement des tests unitaires isoles."
        ),
        runner_role="integration",
        capabilities=["E2E", "Playwright", "parcours utilisateur"],
        inputs=["frontend", "backend", "api_contract"],
        outputs=["e2e_scenarios", "e2e_report"],
        guardrails=["Tester un flux reel de bout en bout."],
    ),
    AgentDefinition(
        id="run_fix",
        name="Execution et correctifs",
        business_role="Run / fix",
        mission="Executer les suites de tests et corriger jusqu'a passage ou echec explicite.",
        runner_role="run_fix",
        capabilities=["execution tests", "diagnostic", "correctifs"],
        inputs=["source_files", "test_files", "e2e_report"],
        outputs=["test_run_report", "fixes_applied", "tests_passed"],
        guardrails=["Ne pas elargir le scope au-dela des tests existants."],
    ),
    AgentDefinition(
        id="review",
        name="Revue de code",
        business_role="Code review",
        mission="Revue de lisibilite, coherence et dette technique evidente.",
        runner_role="review",
        capabilities=["review", "style", "maintenabilite"],
        inputs=["diff", "implementation"],
        outputs=["review_comments", "approval_recommendation"],
        guardrails=["Ne pas re-ecrire toute la feature : commentaires actionnables."],
    ),
    AgentDefinition(
        id="security",
        name="Revue securite",
        business_role="Security",
        mission="Revue securite : auth, secrets, injections, exposition de donnees.",
        runner_role="security",
        capabilities=["OWASP", "auth", "secrets"],
        inputs=["code", "api_contract", "config"],
        outputs=["security_findings", "risk_level"],
        guardrails=["Signaler les risques bloquants avant livraison."],
    ),
    AgentDefinition(
        id="document",
        name="Documentation",
        business_role="Documentation",
        mission="Documenter le livrable, l'usage et les preuves d'execution.",
        runner_role="document",
        capabilities=["README", "doc API", "changelog"],
        inputs=["implementation", "test_run_report", "criteres de succes"],
        outputs=["documentation", "delivery_summary"],
        guardrails=["Ne pas contredire le verdict des tests."],
    ),
    AgentDefinition(
        id="devops",
        name="DevOps / CI",
        business_role="DevOps",
        mission="Preparer CI/CD, conteneurs et notes de deploiement reproductible.",
        runner_role="devops",
        capabilities=["Docker", "CI", "compose"],
        inputs=["repo", "tests", "build"],
        outputs=["ci_pipeline", "deploy_notes"],
        guardrails=["Ne pas modifier le metier : focus livraison technique."],
    ),
]

WORKFLOW_TEAM_TDD = WorkflowDefinition(
    id="team-tdd",
    name="Equipe TDD",
    goal="Livrer une fonctionnalite en Test-Driven Development (full stack).",
    context={"methodology": "test-driven-development"},
    constraints=[
        "Les tests sont ecrits avant le code de production.",
        "Backend puis frontend, puis validation E2E.",
    ],
    success_criteria=[
        "Tests, code, E2E et documentation sont traces.",
        "Le verdict final est explicite.",
    ],
    steps=[
        WorkflowStepDefinition(
            id="tests-first",
            name="Tests d'abord",
            agent_definition_id="write_tests",
            objective="Rediger les tests et criteres d'acceptation avant toute implementation.",
        ),
        WorkflowStepDefinition(
            id="backend",
            name="Backend",
            agent_definition_id="code_backend",
            objective="Implementer l'API et la logique serveur.",
            depends_on=["tests-first"],
        ),
        WorkflowStepDefinition(
            id="frontend",
            name="Frontend",
            agent_definition_id="code_frontend",
            objective="Implementer l'interface et les appels API.",
            depends_on=["backend"],
        ),
        WorkflowStepDefinition(
            id="e2e",
            name="Tests bout-en-bout",
            agent_definition_id="integration",
            objective="Valider le parcours complet UI + API.",
            depends_on=["frontend"],
        ),
        WorkflowStepDefinition(
            id="run-fix",
            name="Execution et correctifs",
            agent_definition_id="run_fix",
            objective="Executer toutes les suites et corriger.",
            depends_on=["e2e"],
        ),
        WorkflowStepDefinition(
            id="document",
            name="Documentation",
            agent_definition_id="document",
            objective="Documenter le livrable et les preuves.",
            depends_on=["run-fix"],
        ),
    ],
)

WORKFLOW_TEAM_CLASSIC = WorkflowDefinition(
    id="team-classic",
    name="Equipe Plan-Code-Test",
    goal="Livrer en approche plan, contrat API, code, tests, E2E, securite, documentation.",
    context={"methodology": "plan-code-test-document"},
    constraints=[
        "Le schema et le contrat API guident l'implementation.",
        "La documentation respecte le verdict des tests.",
    ],
    success_criteria=[
        "Chaque etape produit un livrable trace.",
        "Le workflow est auditable de bout en bout.",
    ],
    steps=[
        WorkflowStepDefinition(
            id="schematic",
            name="Schema et plan",
            agent_definition_id="schematic",
            objective="Produire le schema et le plan d'implementation.",
        ),
        WorkflowStepDefinition(
            id="contract",
            name="Contrat d'API",
            agent_definition_id="api_contract",
            objective="Definir routes et schemas partages avant de coder.",
            depends_on=["schematic"],
        ),
        WorkflowStepDefinition(
            id="database",
            name="Schema base de donnees",
            agent_definition_id="database",
            objective="Preparer migrations et contraintes.",
            depends_on=["contract"],
        ),
        WorkflowStepDefinition(
            id="backend",
            name="Backend",
            agent_definition_id="code_backend",
            objective="Implementer le serveur selon le contrat.",
            depends_on=["database"],
        ),
        WorkflowStepDefinition(
            id="frontend",
            name="Frontend",
            agent_definition_id="code_frontend",
            objective="Implementer l'UI selon le contrat.",
            depends_on=["backend"],
        ),
        WorkflowStepDefinition(
            id="test",
            name="Tests par couche",
            agent_definition_id="test_and_verify",
            objective="Tests automatises sur backend/frontend.",
            depends_on=["frontend"],
        ),
        WorkflowStepDefinition(
            id="e2e",
            name="Tests bout-en-bout",
            agent_definition_id="integration",
            objective="Parcours utilisateur complet (UI + API reelle).",
            depends_on=["test"],
        ),
        WorkflowStepDefinition(
            id="run-fix",
            name="Execution et correctifs",
            agent_definition_id="run_fix",
            objective="Corriger jusqu'a passage des suites.",
            depends_on=["e2e"],
        ),
        WorkflowStepDefinition(
            id="review",
            name="Revue de code",
            agent_definition_id="review",
            objective="Revue de coherence et maintenabilite.",
            depends_on=["run-fix"],
        ),
        WorkflowStepDefinition(
            id="security",
            name="Revue securite",
            agent_definition_id="security",
            objective="Verifier risques securite evidentes.",
            depends_on=["review"],
        ),
        WorkflowStepDefinition(
            id="document",
            name="Documentation",
            agent_definition_id="document",
            objective="Documenter le livrable final.",
            depends_on=["security"],
        ),
    ],
)

_LEGACY_AGENT_RUNNER_PATCHES: dict[str, str] = {
    "director": "plan",
    "analyst": "research",
    "delivery": "execute",
    "quality": "verify",
}


def ensure_dev_team_catalog(catalog: DefinitionCatalog) -> None:
    for agent in DEV_TEAM_AGENT_PRESETS:
        catalog.save_agent(agent, overwrite=True)

    for workflow in (WORKFLOW_TEAM_TDD, WORKFLOW_TEAM_CLASSIC):
        catalog.save_workflow(workflow, overwrite=True)

    for agent in catalog.list_agents():
        patch = _LEGACY_AGENT_RUNNER_PATCHES.get(agent.id)
        if patch and not (agent.runner_role or "").strip():
            catalog.save_agent(agent.model_copy(update={"runner_role": patch}), overwrite=True)
