from __future__ import annotations

import json
from typing import Any

from core.builder.slug import slugify


def _json_load(value: Any) -> Any:
    if isinstance(value, (str, bytes)):
        return json.loads(value)
    return value


def apply_brick_field_update(
    cursor: Any,
    *,
    brick_id: int,
    field_path: str,
    proposed_value: Any,
) -> dict[str, Any]:
    cursor.execute(
        "SELECT id, slug, label, description, metadata FROM builder_bricks WHERE id = %s",
        (brick_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"Unknown brick '{brick_id}'.")

    before = {
        "label": row["label"],
        "description": row.get("description"),
        "metadata": _json_load(row.get("metadata")) or {},
    }
    field = field_path.strip()
    if field == "label":
        cursor.execute(
            "UPDATE builder_bricks SET label = %s, source = 'llm_merged', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (str(proposed_value), brick_id),
        )
    elif field == "description":
        cursor.execute(
            "UPDATE builder_bricks SET description = %s, source = 'llm_merged', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (str(proposed_value) if proposed_value is not None else None, brick_id),
        )
    elif field.startswith("metadata."):
        key = field[len("metadata.") :]
        metadata = dict(before["metadata"])
        metadata[key] = proposed_value
        cursor.execute(
            "UPDATE builder_bricks SET metadata = %s, source = 'llm_merged', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (json.dumps(metadata), brick_id),
        )
    else:
        raise ValueError(f"Unsupported field_path for merge: {field_path!r}")

    cursor.execute(
        "SELECT label, description, metadata FROM builder_bricks WHERE id = %s",
        (brick_id,),
    )
    after_row = cursor.fetchone()
    after = {
        "label": after_row["label"],
        "description": after_row.get("description"),
        "metadata": _json_load(after_row.get("metadata")) or {},
    }
    return {"brick_id": brick_id, "before": before, "after": after}


def create_brick_from_proposal(
    cursor: Any,
    *,
    type_id: int,
    field_path: str,
    proposed_value: Any,
    domain_id: int | None,
    label_fallback: str,
) -> int:
    label = label_fallback
    description: str | None = None
    metadata: dict[str, Any] = {}

    if field_path == "label":
        label = str(proposed_value)
    elif field_path == "description":
        description = str(proposed_value) if proposed_value is not None else None
    elif field_path.startswith("metadata."):
        metadata[field_path[len("metadata.") :]] = proposed_value

    slug = slugify(label)[:128]
    cursor.execute(
        """
        INSERT INTO builder_bricks (type_id, domain_id, slug, label, description, metadata, status, source, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, 'draft_catalog', 'llm_merged', 'llm:proposal')
        """,
        (type_id, domain_id, slug, label[:255], description, json.dumps(metadata)),
    )
    brick_id = int(cursor.lastrowid)
    cursor.execute(
        """
        INSERT INTO builder_brick_versions (brick_id, version, status)
        VALUES (%s, '1.0.0', 'published')
        """,
        (brick_id,),
    )
    return brick_id
