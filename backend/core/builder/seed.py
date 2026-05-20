from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.builder.audit import log_audit_event
from core.builder.connection import connect
from core.builder.slug import slugify
from core.contracts import AgentDefinition, WorkflowDefinition

_DOMAIN_BY_AGENT_PREFIX: dict[str, str] = {
    "doc_": "doc",
    "viz_": "viz",
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "catalog" / "agents").is_dir():
            return parent
    return here.parents[3]


def _catalog_dir() -> Path:
    root = _repo_root()
    catalog = root / "catalog"
    if not catalog.is_dir():
        raise FileNotFoundError(
            f"Répertoire catalogue introuvable: {catalog}. "
            "Vérifiez que catalog/ est présent (Docker: COPY catalog dans l'image)."
        )
    return catalog


def _agent_domain(agent_id: str) -> str:
    for prefix, code in _DOMAIN_BY_AGENT_PREFIX.items():
        if agent_id.startswith(prefix):
            return code
    return "dev"


def _type_id(cursor: Any, code: str) -> int:
    cursor.execute("SELECT id FROM builder_brick_types WHERE code = %s", (code,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Unknown brick type: {code}")
    return int(row["id"])


def _domain_id(cursor: Any, code: str) -> int | None:
    cursor.execute("SELECT id FROM builder_domains WHERE code = %s", (code,))
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def _upsert_brick(
    cursor: Any,
    *,
    type_code: str,
    label: str,
    domain_code: str | None,
    source_text: str | None = None,
    slug: str | None = None,
) -> int:
    slug = slug or slugify(label)
    type_id = _type_id(cursor, type_code)
    domain_id = _domain_id(cursor, domain_code) if domain_code else None
    cursor.execute(
        """
        INSERT INTO builder_bricks (type_id, domain_id, slug, label, description, source)
        VALUES (%s, %s, %s, %s, %s, 'catalog_seed')
        ON DUPLICATE KEY UPDATE label = VALUES(label), updated_at = CURRENT_TIMESTAMP
        """,
        (type_id, domain_id, slug, label, source_text),
    )
    cursor.execute(
        "SELECT id FROM builder_bricks WHERE type_id = %s AND slug = %s",
        (type_id, slug),
    )
    brick_id = int(cursor.fetchone()["id"])
    cursor.execute(
        """
        INSERT INTO builder_brick_versions (brick_id, version, status)
        VALUES (%s, '1.0.0', 'published')
        ON DUPLICATE KEY UPDATE brick_id = brick_id
        """,
        (brick_id,),
    )
    return brick_id


def _materialize_agent_definition(cursor: Any, definition: AgentDefinition) -> None:
    payload = definition.model_dump(mode="json")
    cursor.execute(
        """
        INSERT INTO agent_definitions (id, payload)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE payload = VALUES(payload), updated_at = CURRENT_TIMESTAMP
        """,
        (definition.id, json.dumps(payload)),
    )


def _materialize_workflow_definition(cursor: Any, definition: WorkflowDefinition) -> None:
    payload = definition.model_dump(mode="json")
    cursor.execute(
        """
        INSERT INTO workflow_definitions (id, payload)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE payload = VALUES(payload), updated_at = CURRENT_TIMESTAMP
        """,
        (definition.id, json.dumps(payload)),
    )


def seed_agent_from_file(cursor: Any, path: Path) -> AgentDefinition:
    raw = json.loads(path.read_text(encoding="utf-8"))
    definition = AgentDefinition.model_validate(raw)
    domain_code = _agent_domain(definition.id)

    role_brick = _upsert_brick(
        cursor,
        type_code="role",
        label=definition.business_role,
        domain_code=domain_code,
    )
    composition: list[tuple[str, int, int]] = [( "role", role_brick, 0)]

    for index, value in enumerate(definition.capabilities):
        brick_id = _upsert_brick(cursor, type_code="capability", label=value, domain_code=domain_code)
        composition.append(("capability", brick_id, index))
    for index, value in enumerate(definition.inputs):
        brick_id = _upsert_brick(cursor, type_code="input", label=value, domain_code=domain_code)
        composition.append(("input", brick_id, index))
    for index, value in enumerate(definition.outputs):
        brick_id = _upsert_brick(cursor, type_code="output", label=value, domain_code=domain_code)
        composition.append(("output", brick_id, index))
    for index, value in enumerate(definition.guardrails):
        brick_id = _upsert_brick(
            cursor,
            type_code="guardrail",
            label=value[:255],
            domain_code=domain_code,
            source_text=value,
            slug=f"guardrail-{slugify(value)[:72]}-{index}",
        )
        composition.append(("guardrail", brick_id, index))

    if definition.runner_role:
        cursor.execute(
            """
            INSERT INTO builder_runner_bindings (runner_role, label, implementation_kind)
            VALUES (%s, %s, 'specialist')
            ON DUPLICATE KEY UPDATE label = VALUES(label)
            """,
            (definition.runner_role, definition.name),
        )

    domain_id = _domain_id(cursor, domain_code)
    cursor.execute(
        """
        INSERT INTO builder_agents (id, domain_id) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE domain_id = VALUES(domain_id)
        """,
        (definition.id, domain_id),
    )

    payload = definition.model_dump(mode="json")
    runner = definition.runner_role or None
    cursor.execute(
        """
        INSERT INTO builder_agent_versions (
            agent_id, version, status, payload, runner_role, published_at, published_by, created_by
        ) VALUES (%s, '1.0.0', 'published', %s, %s, CURRENT_TIMESTAMP, 'system:seeder', 'system:seeder')
        ON DUPLICATE KEY UPDATE
            payload = VALUES(payload),
            runner_role = VALUES(runner_role),
            status = 'published'
        """,
        (definition.id, json.dumps(payload), runner),
    )
    cursor.execute(
        """
        SELECT id FROM builder_agent_versions WHERE agent_id = %s AND version = '1.0.0'
        """,
        (definition.id,),
    )
    version_id = int(cursor.fetchone()["id"])

    cursor.execute(
        "DELETE FROM builder_agent_composition WHERE version_id = %s",
        (version_id,),
    )
    for slot, brick_id, sort_order in composition:
        cursor.execute(
            """
            INSERT INTO builder_agent_composition (version_id, brick_id, slot, sort_order)
            VALUES (%s, %s, %s, %s)
            """,
            (version_id, brick_id, slot, sort_order),
        )

    cursor.execute(
        "UPDATE builder_agents SET published_version_id = %s WHERE id = %s",
        (version_id, definition.id),
    )
    _materialize_agent_definition(cursor, definition)
    return definition


def seed_workflow_from_file(cursor: Any, path: Path) -> WorkflowDefinition:
    raw = json.loads(path.read_text(encoding="utf-8"))
    definition = WorkflowDefinition.model_validate(raw)
    domain_code = "dev"
    if definition.id.startswith("documentation"):
        domain_code = "doc"
    elif definition.id.startswith("team-code-viz"):
        domain_code = "viz"
    elif definition.id == "deal-review":
        domain_code = "deal"

    domain_id = _domain_id(cursor, domain_code)
    cursor.execute(
        """
        INSERT INTO builder_workflows (id, domain_id) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE domain_id = VALUES(domain_id)
        """,
        (definition.id, domain_id),
    )

    payload = definition.model_dump(mode="json")
    cursor.execute(
        """
        INSERT INTO builder_workflow_versions (
            workflow_id, version, status, payload, published_at, published_by, created_by
        ) VALUES (%s, '1.0.0', 'published', %s, CURRENT_TIMESTAMP, 'system:seeder', 'system:seeder')
        ON DUPLICATE KEY UPDATE payload = VALUES(payload), status = 'published'
        """,
        (definition.id, json.dumps(payload)),
    )
    cursor.execute(
        "SELECT id FROM builder_workflow_versions WHERE workflow_id = %s AND version = '1.0.0'",
        (definition.id,),
    )
    version_id = int(cursor.fetchone()["id"])

    methodology = definition.context.get("methodology")
    if methodology:
        framework_brick = _upsert_brick(
            cursor,
            type_code="framework",
            label=str(methodology),
            domain_code=domain_code,
        )
        cursor.execute(
            """
            INSERT INTO builder_frameworks (brick_id, framework_kind, template_payload)
            VALUES (%s, 'methodology', %s)
            ON DUPLICATE KEY UPDATE template_payload = VALUES(template_payload)
            """,
            (framework_brick, json.dumps({"methodology": methodology})),
        )
        cursor.execute(
            """
            INSERT IGNORE INTO builder_workflow_frameworks (version_id, framework_brick_id)
            VALUES (%s, %s)
            """,
            (version_id, framework_brick),
        )

    cursor.execute("DELETE FROM builder_workflow_steps WHERE version_id = %s", (version_id,))
    for index, step in enumerate(definition.steps):
        depends = list(step.depends_on)
        cursor.execute(
            """
            INSERT INTO builder_workflow_steps (
                version_id, step_id, name, objective, agent_definition_id,
                depends_on_explicit, depends_on_merged, depends_on_source, sort_order
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'explicit', %s)
            """,
            (
                version_id,
                step.id,
                step.name,
                step.objective,
                step.agent_definition_id,
                json.dumps(depends),
                json.dumps(depends),
                index,
            ),
        )

    cursor.execute(
        "UPDATE builder_workflows SET published_version_id = %s WHERE id = %s",
        (version_id, definition.id),
    )

    cursor.execute(
        """
        INSERT INTO builder_workflow_patterns (code, domain_id, label, is_optional)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE label = VALUES(label)
        """,
        (definition.id, domain_id, definition.name),
    )
    cursor.execute(
        "SELECT id FROM builder_workflow_patterns WHERE code = %s",
        (definition.id,),
    )
    pattern_id = int(cursor.fetchone()["id"])
    cursor.execute(
        "DELETE FROM builder_workflow_pattern_steps WHERE pattern_id = %s",
        (pattern_id,),
    )
    for index, step in enumerate(definition.steps):
        cursor.execute(
            """
            INSERT INTO builder_workflow_pattern_steps (
                pattern_id, step_template, suggested_agent_id, default_depends_on, sort_order
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                pattern_id,
                json.dumps({"id": step.id, "name": step.name, "objective": step.objective}),
                step.agent_definition_id,
                json.dumps(list(step.depends_on)),
                index,
            ),
        )

    _materialize_workflow_definition(cursor, definition)
    return definition


def seed_refactor_bricks(cursor: Any) -> None:
    """S3 — briques génériques sans agent catalogue associé."""
    samples = [
        ("capability", "Programmation fonctionnelle", "refactor"),
        ("capability", "Design patterns", "refactor"),
        ("capability", "Optimisation performance", "refactor"),
        ("guardrail", "Pas de changement de comportement observable", "refactor"),
        ("framework", "Refactoring incrémental", "refactor"),
    ]
    for type_code, label, domain in samples:
        _upsert_brick(cursor, type_code=type_code, label=label, domain_code=domain)


def run_seed(*, log_events: bool = True) -> dict[str, int]:
    agents_dir = _catalog_dir() / "agents"
    workflows_dir = _catalog_dir() / "workflows"
    counts = {"agents": 0, "workflows": 0}

    with connect() as conn:
        with conn.cursor() as cursor:
            for path in sorted(agents_dir.glob("*.json")):
                seed_agent_from_file(cursor, path)
                conn.commit()
                counts["agents"] += 1
            for path in sorted(workflows_dir.glob("*.json")):
                seed_workflow_from_file(cursor, path)
                conn.commit()
                counts["workflows"] += 1
            seed_refactor_bricks(cursor)
            conn.commit()

    if log_events:
        log_audit_event(
            entity_type="builder_seed",
            entity_id="catalog",
            action="materialize_catalog",
            actor_type="system",
            actor_id="system:seeder",
            after_payload=counts,
        )
    return counts


if __name__ == "__main__":
    result = run_seed()
    print(f"Builder seed complete: {result}")
