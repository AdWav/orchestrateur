from core.contracts import AgentDefinition, WorkflowDefinition, WorkflowStepDefinition
from core.definition_catalog import FileDefinitionCatalog


def _seed_agents(catalog: FileDefinitionCatalog) -> None:
    catalog.save_agent(
        AgentDefinition(
            id="director",
            name="Directeur de mission",
            business_role="Direction",
            mission="Cadre la mission.",
        )
    )
    catalog.save_agent(
        AgentDefinition(
            id="analyst",
            name="Analyste senior",
            business_role="Analyse",
            mission="Collecte les signaux.",
        )
    )
    catalog.save_agent(
        AgentDefinition(
            id="delivery",
            name="Responsable delivery",
            business_role="Delivery",
            mission="Prepare le plan d'action.",
        )
    )
    catalog.save_agent(
        AgentDefinition(
            id="quality",
            name="Controle qualite",
            business_role="Qualite",
            mission="Valide le dossier.",
        )
    )


def _build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="pre-audit",
        name="Pre audit",
        goal="Produire un brief de mission executable.",
        context={"company": "Atlas Conseil"},
        constraints=["Rester lisible pour le management."],
        success_criteria=["Le dossier doit rester actionnable."],
        steps=[
            WorkflowStepDefinition(
                id="brief",
                name="Cadrage",
                agent_definition_id="director",
                objective="Cadrer la mission.",
            ),
            WorkflowStepDefinition(
                id="analysis",
                name="Analyse",
                agent_definition_id="analyst",
                objective="Collecter les signaux.",
                depends_on=["brief"],
            ),
            WorkflowStepDefinition(
                id="plan",
                name="Plan d'action",
                agent_definition_id="delivery",
                objective="Transformer l'analyse en plan.",
                depends_on=["analysis"],
            ),
            WorkflowStepDefinition(
                id="validation",
                name="Validation",
                agent_definition_id="quality",
                objective="Valider le dossier final.",
                depends_on=["plan"],
            ),
        ],
    )


def test_file_catalog_persists_agents_and_workflows(tmp_path) -> None:
    catalog = FileDefinitionCatalog(tmp_path)
    _seed_agents(catalog)

    workflow = _build_workflow()
    catalog.save_workflow(workflow)

    assert [definition.id for definition in catalog.list_agents()] == [
        "analyst",
        "delivery",
        "director",
        "quality",
    ]
    assert [definition.id for definition in catalog.list_workflows()] == ["pre-audit"]


def test_file_catalog_rejects_workflow_with_unknown_agent(tmp_path) -> None:
    catalog = FileDefinitionCatalog(tmp_path)

    workflow = WorkflowDefinition(
        id="invalid-workflow",
        name="Invalid workflow",
        goal="Doit etre refuse.",
        steps=[
            WorkflowStepDefinition(
                id="step-1",
                name="Step 1",
                agent_definition_id="missing-agent",
                objective="Impossible a resoudre.",
            )
        ],
    )

    try:
        catalog.save_workflow(workflow)
    except ValueError as exc:
        assert "unknown agents" in str(exc)
    else:
        raise AssertionError("WorkflowDefinition should reject unknown agent references.")


