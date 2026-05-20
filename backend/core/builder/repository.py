from __future__ import annotations

import json
from typing import Any

from core.builder.connection import connect
from core.builder.slug import slugify


class BuilderRepository:
    def list_bricks(
        self,
        *,
        type_code: str | None = None,
        domain_code: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if type_code:
            clauses.append("bt.code = %s")
            params.append(type_code)
        if domain_code:
            clauses.append("d.code = %s")
            params.append(domain_code)
        if status:
            clauses.append("b.status = %s")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT b.id, b.slug, b.label, b.description, b.status, b.source,
                   bt.code AS type_code, d.code AS domain_code
            FROM builder_bricks b
            JOIN builder_brick_types bt ON bt.id = b.type_id
            LEFT JOIN builder_domains d ON d.id = b.domain_id
            {where}
            ORDER BY bt.code, b.slug
        """
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())

    def get_brick(self, brick_id: int) -> dict[str, Any] | None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT b.id, b.slug, b.label, b.description, b.metadata, b.status,
                           bt.code AS type_code, d.code AS domain_code
                    FROM builder_bricks b
                    JOIN builder_brick_types bt ON bt.id = b.type_id
                    LEFT JOIN builder_domains d ON d.id = b.domain_id
                    WHERE b.id = %s
                    """,
                    (brick_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row.get("metadata"), (str, bytes)):
            row["metadata"] = json.loads(row["metadata"])
        return row

    def list_catalog_agents(self) -> list[dict[str, Any]]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT a.id, a.domain_id, av.version AS published_version
                    FROM builder_agents a
                    LEFT JOIN builder_agent_versions av ON av.id = a.published_version_id
                    ORDER BY a.id
                    """
                )
                return list(cursor.fetchall())

    def list_agent_versions(self, agent_id: str) -> list[dict[str, Any]]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, agent_id, version, status, runner_role, published_at, created_at
                    FROM builder_agent_versions
                    WHERE agent_id = %s
                    ORDER BY created_at DESC
                    """,
                    (agent_id,),
                )
                return list(cursor.fetchall())

    def list_pending_brick_proposals(self, *, status: str = "pending") -> list[dict[str, Any]]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, target_brick_id, field_path, proposed_value, status,
                           proposed_by, session_id, created_at
                    FROM builder_pending_brick_proposals
                    WHERE status = %s
                    ORDER BY created_at ASC
                    """,
                    (status,),
                )
                rows = list(cursor.fetchall())
        for row in rows:
            if isinstance(row.get("proposed_value"), (str, bytes)):
                row["proposed_value"] = json.loads(row["proposed_value"])
        return rows

    def list_audit_events(
        self,
        *,
        entity_type: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if entity_type:
            clauses.append("entity_type = %s")
            params.append(entity_type)
        if session_id:
            clauses.append("session_id = %s")
            params.append(session_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, session_id, entity_type, entity_id, entity_version,
                           action, actor_type, actor_id, created_at
                    FROM builder_audit_events
                    {where}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                return list(cursor.fetchall())

    def list_catalog_workflows(self) -> list[dict[str, Any]]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT w.id, w.domain_id, av.version AS published_version
                    FROM builder_workflows w
                    LEFT JOIN builder_workflow_versions av ON av.id = w.published_version_id
                    ORDER BY w.id
                    """
                )
                return list(cursor.fetchall())

    def get_type_id(self, type_code: str) -> int | None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM builder_brick_types WHERE code = %s",
                    (type_code,),
                )
                row = cursor.fetchone()
        return int(row["id"]) if row else None

    def get_domain_id(self, domain_code: str) -> int | None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM builder_domains WHERE code = %s",
                    (domain_code,),
                )
                row = cursor.fetchone()
        return int(row["id"]) if row else None

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
        type_id = self.get_type_id(type_code)
        if type_id is None:
            raise ValueError(f"Unknown brick type '{type_code}'.")
        domain_id = self.get_domain_id(domain_code) if domain_code else None
        brick_slug = (slug or slugify(label))[:128]
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO builder_bricks (
                        type_id, domain_id, slug, label, description, status, source, created_by
                    ) VALUES (%s, %s, %s, %s, %s, 'draft_catalog', 'human', %s)
                    """,
                    (type_id, domain_id, brick_slug, label[:255], description, created_by),
                )
                brick_id = int(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO builder_brick_versions (brick_id, version, status)
                    VALUES (%s, '1.0.0', 'published')
                    """,
                    (brick_id,),
                )
            conn.commit()
        row = self.get_brick(brick_id)
        assert row is not None
        return row
