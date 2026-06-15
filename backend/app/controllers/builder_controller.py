from __future__ import annotations

import json
import uuid
from typing import Any

from core.builder.audit import log_audit_event
from core.builder.compose import (
    materialize_agent_definition,
    materialize_custom_agent_definition,
    materialize_custom_workflow_definition,
    materialize_workflow_definition,
    next_agent_version,
    runtime_id_for_custom_agent,
    runtime_id_for_custom_workflow,
    upsert_runtime_agent,
    upsert_runtime_workflow,
)
from core.builder.connection import connect
from core.builder.pending_agent_merge import apply_agent_field_update
from core.builder.pending_merge import apply_brick_field_update, create_brick_from_proposal
from core.builder.promotion import promote_custom_agent_to_catalog
from core.builder.repository import BuilderRepository
from core.contracts import AgentDefinition, WorkflowDefinition, WorkflowStepDefinition


class BuilderController:
    def __init__(self, repository: BuilderRepository | None = None) -> None:
        self._repository = repository or BuilderRepository()

    def list_bricks(
        self,
        *,
        type_code: str | None = None,
        domain_code: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._repository.list_bricks(
            type_code=type_code,
            domain_code=domain_code,
            status=status,
        )

    def get_brick(self, brick_id: int) -> dict[str, Any]:
        row = self._repository.get_brick(brick_id)
        if row is None:
            raise KeyError(f"Unknown builder brick '{brick_id}'.")
        return row

    def create_brick(
        self,
        *,
        type_code: str,
        label: str,
        domain_code: str | None = None,
        description: str | None = None,
        slug: str | None = None,
        created_by: str = "human:operator",
    ) -> dict[str, Any]:
        row = self._repository.create_brick(
            type_code=type_code,
            label=label,
            domain_code=domain_code,
            description=description,
            slug=slug,
            created_by=created_by,
        )
        log_audit_event(
            entity_type="builder_brick",
            entity_id=str(row["id"]),
            action="create_brick",
            actor_type="human",
            actor_id=created_by,
            after_payload={"slug": row["slug"], "type_code": type_code},
        )
        return row

    def list_catalog_agents(self) -> list[dict[str, Any]]:
        return self._repository.list_catalog_agents()

    def list_catalog_workflows(self) -> list[dict[str, Any]]:
        return self._repository.list_catalog_workflows()

    def list_agent_versions(self, agent_id: str) -> list[dict[str, Any]]:
        return self._repository.list_agent_versions(agent_id)

    def list_pending_brick_proposals(self) -> list[dict[str, Any]]:
        return self._repository.list_pending_brick_proposals()

    def create_pending_brick_proposal(
        self,
        *,
        field_path: str,
        proposed_value: Any,
        target_brick_id: int | None = None,
        type_code: str | None = None,
        session_id: str | None = None,
        proposed_by: str = "llm",
    ) -> dict[str, Any]:
        if proposed_by not in {"llm", "human"}:
            raise ValueError("proposed_by must be 'llm' or 'human'.")
        type_id = None
        if type_code:
            type_id = self._repository.get_type_id(type_code)
            if type_id is None:
                raise ValueError(f"Unknown brick type '{type_code}'.")

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_pending_brick_proposals (
                        session_id, proposed_by, target_brick_id, proposed_type_id,
                        field_path, proposed_value
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session_id,
                        proposed_by,
                        target_brick_id,
                        type_id,
                        field_path,
                        json.dumps(proposed_value),
                    ),
                )
                proposal_id = int(cursor.lastrowid)
            conn.commit()

        log_audit_event(
            entity_type="builder_pending_brick",
            entity_id=str(proposal_id),
            action="create_proposal",
            actor_type="llm" if proposed_by == "llm" else "human",
            actor_id=f"{proposed_by}:proposal",
            session_id=session_id,
            after_payload={"field_path": field_path, "target_brick_id": target_brick_id},
        )
        return {
            "id": proposal_id,
            "status": "pending",
            "field_path": field_path,
            "target_brick_id": target_brick_id,
        }

    def approve_pending_brick(
        self,
        proposal_id: int,
        *,
        reviewer_id: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, target_brick_id, proposed_type_id, field_path,
                           proposed_value, status
                    FROM builder_pending_brick_proposals WHERE id = %s
                    """,
                    (proposal_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown pending proposal '{proposal_id}'.")
                if row["status"] != "pending":
                    raise ValueError(f"Proposal '{proposal_id}' is not pending.")

                proposed_value = row["proposed_value"]
                if isinstance(proposed_value, (str, bytes)):
                    proposed_value = json.loads(proposed_value)

                merged_brick_id: int | None = row["target_brick_id"]
                merge_result: dict[str, Any] | None = None

                if merged_brick_id is not None:
                    merge_result = apply_brick_field_update(
                        cursor,
                        brick_id=int(merged_brick_id),
                        field_path=str(row["field_path"]),
                        proposed_value=proposed_value,
                    )
                elif row["proposed_type_id"] is not None:
                    merged_brick_id = create_brick_from_proposal(
                        cursor,
                        type_id=int(row["proposed_type_id"]),
                        field_path=str(row["field_path"]),
                        proposed_value=proposed_value,
                        domain_id=None,
                        label_fallback=str(proposed_value)[:255],
                    )
                    merge_result = {"brick_id": merged_brick_id, "created": True}
                else:
                    raise ValueError(
                        "Proposal requires target_brick_id or type_code (proposed_type_id)."
                    )

                cursor.execute(
                    """
                    UPDATE builder_pending_brick_proposals
                    SET status = 'approved',
                        reviewed_by = %s,
                        reviewed_at = CURRENT_TIMESTAMP,
                        merged_brick_id = %s
                    WHERE id = %s
                    """,
                    (reviewer_id, merged_brick_id, proposal_id),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_pending_brick",
            entity_id=str(proposal_id),
            action="approve_pending",
            actor_type="human",
            actor_id=reviewer_id,
            after_payload={"status": "approved", "merged_brick_id": merged_brick_id, "merge": merge_result},
        )
        return {
            "id": proposal_id,
            "status": "approved",
            "merged_brick_id": merged_brick_id,
        }

    def reject_pending_brick(
        self,
        proposal_id: int,
        *,
        reviewer_id: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM builder_pending_brick_proposals WHERE id = %s",
                    (proposal_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown pending proposal '{proposal_id}'.")
                cursor.execute(
                    """
                    UPDATE builder_pending_brick_proposals
                    SET status = 'rejected', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (reviewer_id, proposal_id),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_pending_brick",
            entity_id=str(proposal_id),
            action="reject_pending",
            actor_type="human",
            actor_id=reviewer_id,
            after_payload={"status": "rejected"},
        )
        return {"id": proposal_id, "status": "rejected"}

    def create_agent_draft(
        self,
        *,
        agent_id: str,
        name: str,
        mission: str,
        composition: list[dict[str, Any]],
        domain_code: str | None = "dev",
        runner_role: str | None = None,
        business_role: str | None = None,
        created_by: str = "human:operator",
    ) -> dict[str, Any]:
        domain_id = self._repository.get_domain_id(domain_code) if domain_code else None
        role_label = business_role or name
        payload = {
            "id": agent_id,
            "name": name,
            "business_role": role_label,
            "mission": mission,
            "runner_role": runner_role or "",
        }

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_agents (id, domain_id) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE domain_id = VALUES(domain_id)
                    """,
                    (agent_id, domain_id),
                )
                comp_rows = [
                    {
                        "slot": item["slot"],
                        "brick_id": int(item["brick_id"]),
                        "sort_order": int(item.get("sort_order", index)),
                    }
                    for index, item in enumerate(composition)
                ]
                version_str = next_agent_version(cursor, agent_id, current_rows=comp_rows)
                cursor.execute(
                    """
                    INSERT INTO builder_agent_versions (
                        agent_id, version, status, payload, runner_role, created_by
                    ) VALUES (%s, %s, 'draft', %s, %s, %s)
                    """,
                    (
                        agent_id,
                        version_str,
                        json.dumps(payload),
                        runner_role,
                        created_by,
                    ),
                )
                version_id = int(cursor.lastrowid)
                for item in comp_rows:
                    cursor.execute(
                        """
                        INSERT INTO builder_agent_composition (
                            version_id, brick_id, slot, sort_order
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (
                            version_id,
                            item["brick_id"],
                            item["slot"],
                            item["sort_order"],
                        ),
                    )
            conn.commit()

        log_audit_event(
            entity_type="builder_agent_version",
            entity_id=str(version_id),
            entity_version=version_str,
            action="create_draft",
            actor_type="human",
            actor_id=created_by,
            after_payload={"agent_id": agent_id},
        )
        return {
            "agent_id": agent_id,
            "version_id": version_id,
            "version": version_str,
            "status": "draft",
        }

    def publish_agent_version(
        self,
        version_id: int,
        *,
        published_by: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, agent_id, version, status, payload, runner_role
                    FROM builder_agent_versions WHERE id = %s
                    """,
                    (version_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown agent version '{version_id}'.")
                if row["status"] != "draft":
                    raise ValueError(f"Version '{version_id}' is not a draft.")

                payload = row["payload"]
                if isinstance(payload, (str, bytes)):
                    payload = json.loads(payload)

                definition = materialize_agent_definition(
                    cursor, version_id=int(row["id"]), payload=payload
                )
                AgentDefinition.model_validate(definition.model_dump())

                cursor.execute(
                    """
                    UPDATE builder_agent_versions
                    SET status = 'archived'
                    WHERE agent_id = %s AND status = 'published'
                    """,
                    (row["agent_id"],),
                )
                cursor.execute(
                    """
                    UPDATE builder_agent_versions
                    SET status = 'published',
                        published_at = CURRENT_TIMESTAMP,
                        published_by = %s,
                        payload = %s
                    WHERE id = %s
                    """,
                    (
                        published_by,
                        json.dumps(definition.model_dump(mode="json")),
                        version_id,
                    ),
                )
                cursor.execute(
                    "UPDATE builder_agents SET published_version_id = %s WHERE id = %s",
                    (version_id, row["agent_id"]),
                )
                upsert_runtime_agent(cursor, definition)
            conn.commit()

        log_audit_event(
            entity_type="builder_agent",
            entity_id=str(row["agent_id"]),
            entity_version=str(row["version"]),
            action="publish",
            actor_type="human",
            actor_id=published_by,
            after_payload={"version_id": version_id},
        )
        return {
            "agent_id": row["agent_id"],
            "version_id": version_id,
            "version": row["version"],
            "status": "published",
        }

    def create_workflow_draft(
        self,
        *,
        workflow_id: str,
        name: str,
        goal: str,
        steps: list[dict[str, Any]],
        context: dict[str, str] | None = None,
        constraints: list[str] | None = None,
        success_criteria: list[str] | None = None,
        domain_code: str | None = "dev",
        created_by: str = "human:operator",
    ) -> dict[str, Any]:
        domain_id = self._repository.get_domain_id(domain_code) if domain_code else None
        step_models = [
            WorkflowStepDefinition.model_validate(
                {
                    "id": step["id"],
                    "name": step["name"],
                    "agent_definition_id": step["agent_definition_id"],
                    "objective": step["objective"],
                    "depends_on": step.get("depends_on") or [],
                    "runner_role": step.get("runner_role"),
                }
            )
            for step in steps
        ]
        draft = WorkflowDefinition(
            id=workflow_id,
            name=name,
            goal=goal,
            context=context or {},
            constraints=constraints or [],
            success_criteria=success_criteria or [],
            steps=step_models,
        )
        payload = draft.model_dump(mode="json")

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_workflows (id, domain_id) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE domain_id = VALUES(domain_id)
                    """,
                    (workflow_id, domain_id),
                )
                cursor.execute(
                    """
                    SELECT version FROM builder_workflow_versions
                    WHERE workflow_id = %s AND status = 'published'
                    ORDER BY published_at DESC LIMIT 1
                    """,
                    (workflow_id,),
                )
                published = cursor.fetchone()
                version_str = "1.0.0"
                if published:
                    parts = str(published["version"]).split(".")
                    version_str = f"{parts[0]}.{int(parts[1]) + 1}.0"

                cursor.execute(
                    """
                    INSERT INTO builder_workflow_versions (
                        workflow_id, version, status, payload, created_by
                    ) VALUES (%s, %s, 'draft', %s, %s)
                    """,
                    (workflow_id, version_str, json.dumps(payload), created_by),
                )
                version_id = int(cursor.lastrowid)

                cursor.execute(
                    "DELETE FROM builder_workflow_steps WHERE version_id = %s",
                    (version_id,),
                )
                for index, step in enumerate(step_models):
                    explicit = list(step.depends_on)
                    cursor.execute(
                        """
                        INSERT INTO builder_workflow_steps (
                            version_id, step_id, name, objective, agent_definition_id,
                            depends_on_explicit, depends_on_merged, depends_on_source, sort_order,
                            runner_role_override
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'explicit', %s, %s)
                        """,
                        (
                            version_id,
                            step.id,
                            step.name,
                            step.objective,
                            step.agent_definition_id,
                            json.dumps(explicit),
                            json.dumps(explicit),
                            index,
                            step.runner_role,
                        ),
                    )
            conn.commit()

        log_audit_event(
            entity_type="builder_workflow_version",
            entity_id=str(version_id),
            entity_version=version_str,
            action="create_draft",
            actor_type="human",
            actor_id=created_by,
            after_payload={"workflow_id": workflow_id},
        )
        return {
            "workflow_id": workflow_id,
            "version_id": version_id,
            "version": version_str,
            "status": "draft",
        }

    def publish_workflow_version(
        self,
        version_id: int,
        *,
        published_by: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, workflow_id, version, status, payload
                    FROM builder_workflow_versions WHERE id = %s
                    """,
                    (version_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown workflow version '{version_id}'.")
                if row["status"] != "draft":
                    raise ValueError(f"Version '{version_id}' is not a draft.")

                payload = row["payload"]
                if isinstance(payload, (str, bytes)):
                    payload = json.loads(payload)

                definition = materialize_workflow_definition(
                    cursor, version_id=int(row["id"]), payload=payload
                )
                WorkflowDefinition.model_validate(definition.model_dump())

                cursor.execute(
                    """
                    UPDATE builder_workflow_versions
                    SET status = 'archived'
                    WHERE workflow_id = %s AND status = 'published'
                    """,
                    (row["workflow_id"],),
                )
                cursor.execute(
                    """
                    UPDATE builder_workflow_versions
                    SET status = 'published',
                        published_at = CURRENT_TIMESTAMP,
                        published_by = %s,
                        payload = %s
                    WHERE id = %s
                    """,
                    (
                        published_by,
                        json.dumps(definition.model_dump(mode="json")),
                        version_id,
                    ),
                )
                cursor.execute(
                    "UPDATE builder_workflows SET published_version_id = %s WHERE id = %s",
                    (version_id, row["workflow_id"]),
                )
                upsert_runtime_workflow(cursor, definition)
            conn.commit()

        log_audit_event(
            entity_type="builder_workflow",
            entity_id=str(row["workflow_id"]),
            entity_version=str(row["version"]),
            action="publish",
            actor_type="human",
            actor_id=published_by,
            after_payload={"version_id": version_id},
        )
        return {
            "workflow_id": row["workflow_id"],
            "version_id": version_id,
            "version": row["version"],
            "status": "published",
        }

    def create_custom_agent_draft(
        self,
        *,
        slug: str,
        name: str,
        mission: str,
        composition: list[dict[str, Any]],
        owner_user_id: str,
        workspace_id: str | None = None,
        runner_role: str | None = None,
        business_role: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        custom_id = str(uuid.uuid4())
        author = created_by or owner_user_id
        payload = {
            "slug": slug,
            "name": name,
            "business_role": business_role or name,
            "mission": mission,
            "runner_role": runner_role or "",
        }

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_custom_agents (id, workspace_id, owner_user_id, slug)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (custom_id, workspace_id, owner_user_id, slug[:128]),
                )
                cursor.execute(
                    """
                    INSERT INTO builder_custom_agent_versions (
                        custom_agent_id, version, status, payload, runner_role, created_by
                    ) VALUES (%s, '1.0.0', 'draft', %s, %s, %s)
                    """,
                    (custom_id, json.dumps(payload), runner_role, author),
                )
                version_id = int(cursor.lastrowid)
                for index, item in enumerate(composition):
                    cursor.execute(
                        """
                        INSERT INTO builder_custom_agent_composition (
                            version_id, brick_id, slot, sort_order
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (
                            version_id,
                            int(item["brick_id"]),
                            item["slot"],
                            int(item.get("sort_order", index)),
                        ),
                    )
            conn.commit()

        log_audit_event(
            entity_type="builder_custom_agent",
            entity_id=custom_id,
            entity_version="1.0.0",
            action="create_draft",
            actor_type="human",
            actor_id=author,
            after_payload={"slug": slug},
        )
        return {
            "custom_agent_id": custom_id,
            "version_id": version_id,
            "version": "1.0.0",
            "status": "draft",
        }

    def publish_custom_agent_version(
        self,
        version_id: int,
        *,
        published_by: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT v.id, v.custom_agent_id, v.version, v.status, v.payload, v.runner_role,
                           a.slug
                    FROM builder_custom_agent_versions v
                    JOIN builder_custom_agents a ON a.id = v.custom_agent_id
                    WHERE v.id = %s
                    """,
                    (version_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown custom agent version '{version_id}'.")
                if row["status"] != "draft":
                    raise ValueError(f"Version '{version_id}' is not a draft.")

                payload = row["payload"]
                if isinstance(payload, (str, bytes)):
                    payload = json.loads(payload)

                definition = materialize_custom_agent_definition(
                    cursor,
                    version_id=int(row["id"]),
                    slug=str(row["slug"]),
                    payload=payload,
                )
                AgentDefinition.model_validate(definition.model_dump())

                cursor.execute(
                    """
                    UPDATE builder_custom_agent_versions
                    SET status = 'archived'
                    WHERE custom_agent_id = %s AND status = 'published'
                    """,
                    (row["custom_agent_id"],),
                )
                cursor.execute(
                    """
                    UPDATE builder_custom_agent_versions
                    SET status = 'published',
                        payload = %s,
                        runner_role = %s
                    WHERE id = %s
                    """,
                    (
                        json.dumps(definition.model_dump(mode="json")),
                        row.get("runner_role"),
                        version_id,
                    ),
                )
                upsert_runtime_agent(cursor, definition)
            conn.commit()

        runtime_id = runtime_id_for_custom_agent(str(row["slug"]))
        log_audit_event(
            entity_type="builder_custom_agent",
            entity_id=str(row["custom_agent_id"]),
            entity_version=str(row["version"]),
            action="publish",
            actor_type="human",
            actor_id=published_by,
            after_payload={"version_id": version_id, "runtime_agent_id": runtime_id},
        )
        return {
            "custom_agent_id": row["custom_agent_id"],
            "version_id": version_id,
            "version": row["version"],
            "status": "published",
            "runtime_agent_id": runtime_id,
        }

    def create_custom_workflow_draft(
        self,
        *,
        slug: str,
        name: str,
        goal: str,
        steps: list[dict[str, Any]],
        owner_user_id: str,
        workspace_id: str | None = None,
        context: dict[str, str] | None = None,
        constraints: list[str] | None = None,
        success_criteria: list[str] | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        custom_id = str(uuid.uuid4())
        author = created_by or owner_user_id
        step_models = [
            WorkflowStepDefinition.model_validate(
                {
                    "id": step["id"],
                    "name": step["name"],
                    "agent_definition_id": step["agent_definition_id"],
                    "objective": step["objective"],
                    "depends_on": step.get("depends_on") or [],
                    "runner_role": step.get("runner_role"),
                }
            )
            for step in steps
        ]
        runtime_wf_id = runtime_id_for_custom_workflow(slug)
        draft = WorkflowDefinition(
            id=runtime_wf_id,
            name=name,
            goal=goal,
            context=context or {},
            constraints=constraints or [],
            success_criteria=success_criteria or [],
            steps=step_models,
        )
        payload = draft.model_dump(mode="json")

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_custom_workflows (id, workspace_id, owner_user_id, slug)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (custom_id, workspace_id, owner_user_id, slug[:128]),
                )
                cursor.execute(
                    """
                    INSERT INTO builder_custom_workflow_versions (
                        custom_workflow_id, version, status, payload, created_by
                    ) VALUES (%s, '1.0.0', 'draft', %s, %s)
                    """,
                    (custom_id, json.dumps(payload), author),
                )
                version_id = int(cursor.lastrowid)
                for index, step in enumerate(step_models):
                    explicit = list(step.depends_on)
                    cursor.execute(
                        """
                        INSERT INTO builder_custom_workflow_steps (
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
                            json.dumps(explicit),
                            json.dumps(explicit),
                            index,
                        ),
                    )
            conn.commit()

        log_audit_event(
            entity_type="builder_custom_workflow",
            entity_id=custom_id,
            entity_version="1.0.0",
            action="create_draft",
            actor_type="human",
            actor_id=author,
            after_payload={"slug": slug},
        )
        return {
            "custom_workflow_id": custom_id,
            "version_id": version_id,
            "version": "1.0.0",
            "status": "draft",
        }

    def publish_custom_workflow_version(
        self,
        version_id: int,
        *,
        published_by: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT v.id, v.custom_workflow_id, v.version, v.status, v.payload,
                           w.slug
                    FROM builder_custom_workflow_versions v
                    JOIN builder_custom_workflows w ON w.id = v.custom_workflow_id
                    WHERE v.id = %s
                    """,
                    (version_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown custom workflow version '{version_id}'.")
                if row["status"] != "draft":
                    raise ValueError(f"Version '{version_id}' is not a draft.")

                payload = row["payload"]
                if isinstance(payload, (str, bytes)):
                    payload = json.loads(payload)

                definition = materialize_custom_workflow_definition(
                    cursor,
                    version_id=int(row["id"]),
                    slug=str(row["slug"]),
                    payload=payload,
                )
                WorkflowDefinition.model_validate(definition.model_dump())

                cursor.execute(
                    """
                    UPDATE builder_custom_workflow_versions
                    SET status = 'archived'
                    WHERE custom_workflow_id = %s AND status = 'published'
                    """,
                    (row["custom_workflow_id"],),
                )
                cursor.execute(
                    """
                    UPDATE builder_custom_workflow_versions
                    SET status = 'published', payload = %s WHERE id = %s
                    """,
                    (json.dumps(definition.model_dump(mode="json")), version_id),
                )
                upsert_runtime_workflow(cursor, definition)
            conn.commit()

        runtime_id = runtime_id_for_custom_workflow(str(row["slug"]))
        log_audit_event(
            entity_type="builder_custom_workflow",
            entity_id=str(row["custom_workflow_id"]),
            entity_version=str(row["version"]),
            action="publish",
            actor_type="human",
            actor_id=published_by,
            after_payload={"version_id": version_id, "runtime_workflow_id": runtime_id},
        )
        return {
            "custom_workflow_id": row["custom_workflow_id"],
            "version_id": version_id,
            "version": row["version"],
            "status": "published",
            "runtime_workflow_id": runtime_id,
        }

    def list_custom_workflows(
        self,
        *,
        owner_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if owner_user_id:
            clauses.append("owner_user_id = %s")
            params.append(owner_user_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT w.id, w.slug, w.workspace_id, w.owner_user_id, w.created_at,
                           v.id AS version_id, v.version, v.status
                    FROM builder_custom_workflows w
                    LEFT JOIN builder_custom_workflow_versions v
                        ON v.custom_workflow_id = w.id AND v.status = 'draft'
                    {where}
                    ORDER BY w.created_at DESC
                    """,
                    params,
                )
                return list(cursor.fetchall())

    def list_pending_agent_proposals(
        self,
        *,
        draft_version_id: int | None = None,
        status: str = "pending",
    ) -> list[dict[str, Any]]:
        clauses = ["status = %s"]
        params: list[Any] = [status]
        if draft_version_id is not None:
            clauses.append("draft_version_id = %s")
            params.append(draft_version_id)
        where = " AND ".join(clauses)
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, draft_version_id, field_path, proposed_value, previous_value,
                           status, proposed_by, session_id, created_at
                    FROM builder_pending_agent_field_proposals
                    WHERE {where}
                    ORDER BY created_at ASC
                    """,
                    params,
                )
                rows = list(cursor.fetchall())
        for row in rows:
            for key in ("proposed_value", "previous_value"):
                if isinstance(row.get(key), (str, bytes)):
                    row[key] = json.loads(row[key])
        return rows

    def create_pending_agent_proposal(
        self,
        *,
        draft_version_id: int,
        field_path: str,
        proposed_value: Any,
        session_id: str | None = None,
        proposed_by: str = "llm",
    ) -> dict[str, Any]:
        if proposed_by not in {"llm", "human"}:
            raise ValueError("proposed_by must be 'llm' or 'human'.")
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM builder_agent_versions WHERE id = %s",
                    (draft_version_id,),
                )
                version = cursor.fetchone()
                if version is None:
                    raise KeyError(f"Unknown draft version '{draft_version_id}'.")
                if version["status"] != "draft":
                    raise ValueError("Proposals only apply to catalog agent drafts.")
                cursor.execute(
                    """
                    INSERT INTO builder_pending_agent_field_proposals (
                        draft_version_id, field_path, proposed_value, session_id, proposed_by
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        draft_version_id,
                        field_path,
                        json.dumps(proposed_value),
                        session_id,
                        proposed_by,
                    ),
                )
                proposal_id = int(cursor.lastrowid)
            conn.commit()

        log_audit_event(
            entity_type="builder_pending_agent",
            entity_id=str(proposal_id),
            action="create_proposal",
            actor_type="llm" if proposed_by == "llm" else "human",
            actor_id=f"{proposed_by}:proposal",
            session_id=session_id,
            after_payload={"draft_version_id": draft_version_id, "field_path": field_path},
        )
        return {"id": proposal_id, "status": "pending", "draft_version_id": draft_version_id}

    def approve_pending_agent(
        self,
        proposal_id: int,
        *,
        reviewer_id: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, draft_version_id, field_path, proposed_value, status
                    FROM builder_pending_agent_field_proposals WHERE id = %s
                    """,
                    (proposal_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown pending agent proposal '{proposal_id}'.")
                if row["status"] != "pending":
                    raise ValueError(f"Proposal '{proposal_id}' is not pending.")

                proposed_value = row["proposed_value"]
                if isinstance(proposed_value, (str, bytes)):
                    proposed_value = json.loads(proposed_value)

                merge_result = apply_agent_field_update(
                    cursor,
                    version_id=int(row["draft_version_id"]),
                    field_path=str(row["field_path"]),
                    proposed_value=proposed_value,
                )
                cursor.execute(
                    """
                    UPDATE builder_pending_agent_field_proposals
                    SET status = 'approved', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (reviewer_id, proposal_id),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_pending_agent",
            entity_id=str(proposal_id),
            action="approve_pending",
            actor_type="human",
            actor_id=reviewer_id,
            after_payload={"status": "approved", "merge": merge_result},
        )
        return {
            "id": proposal_id,
            "status": "approved",
            "draft_version_id": row["draft_version_id"],
        }

    def reject_pending_agent(
        self,
        proposal_id: int,
        *,
        reviewer_id: str = "human:operator",
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM builder_pending_agent_field_proposals WHERE id = %s",
                    (proposal_id,),
                )
                if cursor.fetchone() is None:
                    raise KeyError(f"Unknown pending agent proposal '{proposal_id}'.")
                cursor.execute(
                    """
                    UPDATE builder_pending_agent_field_proposals
                    SET status = 'rejected', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (reviewer_id, proposal_id),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_pending_agent",
            entity_id=str(proposal_id),
            action="reject_pending",
            actor_type="human",
            actor_id=reviewer_id,
            after_payload={"status": "rejected"},
        )
        return {"id": proposal_id, "status": "rejected"}

    def submit_promotion(
        self,
        *,
        requester_id: str,
        source_kind: str,
        source_id: str,
        target_kind: str,
        proposed_payload: dict[str, Any],
        target_id: str | None = None,
    ) -> dict[str, Any]:
        allowed_source = {"custom_agent", "custom_workflow", "custom_brick_set", "pending_brick_batch"}
        allowed_target = {"builder_brick", "builder_agent", "builder_workflow"}
        if source_kind not in allowed_source:
            raise ValueError(f"Invalid source_kind '{source_kind}'.")
        if target_kind not in allowed_target:
            raise ValueError(f"Invalid target_kind '{target_kind}'.")

        with connect() as conn:
            with conn.cursor() as cursor:
                if source_kind == "custom_agent":
                    cursor.execute(
                        """
                        SELECT id FROM builder_custom_agent_versions
                        WHERE custom_agent_id = %s AND status = 'published'
                        """,
                        (source_id,),
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("Custom agent must be published before promotion.")

                cursor.execute(
                    """
                    INSERT INTO builder_promotion_requests (
                        requester_id, source_kind, source_id, target_kind, target_id, proposed_payload
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        requester_id,
                        source_kind,
                        source_id,
                        target_kind,
                        target_id,
                        json.dumps(proposed_payload),
                    ),
                )
                request_id = int(cursor.lastrowid)
            conn.commit()

        log_audit_event(
            entity_type="builder_promotion",
            entity_id=str(request_id),
            action="submit",
            actor_type="human",
            actor_id=requester_id,
            after_payload={"source_kind": source_kind, "source_id": source_id},
        )
        return self._get_promotion(request_id)

    def list_promotions(
        self,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = %s")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, requester_id, source_kind, source_id, target_kind, target_id,
                           proposed_payload, status, reviewer_id, created_at, resolved_at
                    FROM builder_promotion_requests
                    {where}
                    ORDER BY created_at DESC
                    """,
                    params,
                )
                rows = list(cursor.fetchall())
        for row in rows:
            if isinstance(row.get("proposed_payload"), (str, bytes)):
                row["proposed_payload"] = json.loads(row["proposed_payload"])
        return rows

    def approve_promotion(
        self,
        request_id: int,
        *,
        reviewer_id: str = "human:operator",
        review_notes: str | None = None,
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, source_kind, source_id, target_kind, target_id, proposed_payload, status
                    FROM builder_promotion_requests WHERE id = %s
                    """,
                    (request_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown promotion request '{request_id}'.")
                if row["status"] not in {"submitted", "in_review"}:
                    raise ValueError(f"Promotion '{request_id}' cannot be approved.")

                payload = row["proposed_payload"]
                if isinstance(payload, (str, bytes)):
                    payload = json.loads(payload)

                result_catalog_version_id: int | None = None
                catalog_agent_id: str | None = None

                if row["source_kind"] == "custom_agent" and row["target_kind"] == "builder_agent":
                    catalog_agent_id = row["target_id"] or payload.get("catalog_agent_id")
                    if not catalog_agent_id:
                        raise ValueError("catalog_agent_id required in target_id or proposed_payload.")
                    domain_code = payload.get("domain_code", "dev")
                    domain_id = self._repository.get_domain_id(str(domain_code))
                    promo = promote_custom_agent_to_catalog(
                        cursor,
                        custom_agent_id=str(row["source_id"]),
                        catalog_agent_id=str(catalog_agent_id),
                        domain_id=domain_id,
                        published_by=reviewer_id,
                    )
                    result_catalog_version_id = int(promo["catalog_version_id"])
                    catalog_agent_id = str(promo["catalog_agent_id"])
                else:
                    raise ValueError(
                        f"Promotion pair {row['source_kind']} -> {row['target_kind']} not implemented."
                    )

                cursor.execute(
                    """
                    UPDATE builder_promotion_requests
                    SET status = 'approved',
                        reviewer_id = %s,
                        review_notes = %s,
                        result_catalog_version_id = %s,
                        resolved_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (reviewer_id, review_notes, result_catalog_version_id, request_id),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_promotion",
            entity_id=str(request_id),
            action="approve",
            actor_type="human",
            actor_id=reviewer_id,
            after_payload={
                "catalog_agent_id": catalog_agent_id,
                "catalog_version_id": result_catalog_version_id,
            },
        )
        row = self._get_promotion(request_id)
        row["catalog_agent_id"] = catalog_agent_id
        row["catalog_version_id"] = result_catalog_version_id
        return row

    def reject_promotion(
        self,
        request_id: int,
        *,
        reviewer_id: str = "human:operator",
        review_notes: str | None = None,
    ) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, status FROM builder_promotion_requests WHERE id = %s",
                    (request_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown promotion request '{request_id}'.")
                cursor.execute(
                    """
                    UPDATE builder_promotion_requests
                    SET status = 'rejected',
                        reviewer_id = %s,
                        review_notes = %s,
                        resolved_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (reviewer_id, review_notes, request_id),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_promotion",
            entity_id=str(request_id),
            action="reject",
            actor_type="human",
            actor_id=reviewer_id,
            after_payload={"status": "rejected"},
        )
        return self._get_promotion(request_id)

    def create_session(
        self,
        *,
        kind: str,
        actor_type: str,
        actor_id: str,
        goal_prompt: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if kind not in {"agent", "workflow", "brick"}:
            raise ValueError("kind must be agent, workflow, or brick.")
        if actor_type not in {"human", "llm", "system"}:
            raise ValueError("actor_type must be human, llm, or system.")
        sid = session_id or str(uuid.uuid4())
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_composition_sessions (
                        id, kind, actor_type, actor_id, goal_prompt
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (sid, kind, actor_type, actor_id, goal_prompt),
                )
            conn.commit()

        log_audit_event(
            entity_type="builder_session",
            entity_id=sid,
            action="start",
            actor_type=actor_type,
            actor_id=actor_id,
            session_id=sid,
            after_payload={"kind": kind},
        )
        return {"id": sid, "kind": kind, "actor_type": actor_type, "actor_id": actor_id}

    def get_session(self, session_id: str) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, kind, actor_type, actor_id, goal_prompt, started_at, ended_at
                    FROM builder_composition_sessions WHERE id = %s
                    """,
                    (session_id,),
                )
                session = cursor.fetchone()
                if session is None:
                    raise KeyError(f"Unknown session '{session_id}'.")

                cursor.execute(
                    """
                    SELECT id, ref_kind, ref_id
                    FROM builder_composition_session_inputs
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                inputs = list(cursor.fetchall())

                cursor.execute(
                    """
                    SELECT id, entity_kind, entity_version_id, draft_payload
                    FROM builder_composition_session_outputs
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                outputs = list(cursor.fetchall())
                for output in outputs:
                    if isinstance(output.get("draft_payload"), (str, bytes)):
                        output["draft_payload"] = json.loads(output["draft_payload"])

        audit = self._repository.list_audit_events(session_id=session_id, limit=200)
        return {
            "session": session,
            "inputs": inputs,
            "outputs": outputs,
            "audit_events": audit,
        }

    def _get_promotion(self, request_id: int) -> dict[str, Any]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, requester_id, source_kind, source_id, target_kind, target_id,
                           proposed_payload, status, reviewer_id, created_at, resolved_at,
                           result_catalog_version_id AS catalog_version_id
                    FROM builder_promotion_requests
                    WHERE id = %s
                    """,
                    (request_id,),
                )
                row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Unknown promotion request '{request_id}'.")
        if isinstance(row.get("proposed_payload"), (str, bytes)):
            row["proposed_payload"] = json.loads(row["proposed_payload"])
        catalog_version_id = row.pop("catalog_version_id", None)
        if catalog_version_id is not None:
            row["catalog_version_id"] = int(catalog_version_id)
        if row["status"] == "approved" and row.get("target_id"):
            row["catalog_agent_id"] = row["target_id"]
        return row

    def list_custom_agents(
        self,
        *,
        owner_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if owner_user_id:
            clauses.append("a.owner_user_id = %s")
            params.append(owner_user_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT a.id, a.slug, a.workspace_id, a.owner_user_id, a.created_at,
                           v.id AS version_id, v.version, v.status
                    FROM builder_custom_agents a
                    LEFT JOIN (
                        SELECT v1.custom_agent_id, v1.id, v1.version, v1.status
                        FROM builder_custom_agent_versions v1
                        INNER JOIN (
                            SELECT custom_agent_id, MAX(id) AS max_version_id
                            FROM builder_custom_agent_versions
                            GROUP BY custom_agent_id
                        ) latest ON latest.max_version_id = v1.id
                    ) v ON v.custom_agent_id = a.id
                    {where}
                    ORDER BY a.created_at DESC
                    """,
                    params,
                )
                return list(cursor.fetchall())

    def list_audit_events(
        self,
        *,
        entity_type: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._repository.list_audit_events(
            entity_type=entity_type,
            session_id=session_id,
            limit=limit,
        )
