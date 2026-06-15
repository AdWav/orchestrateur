"""Integration smoke test for the builder custom-agent → promotion flow (requires running API)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API_BASE = os.environ.get("BUILDER_API_BASE", "http://localhost:8000").rstrip("/")


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = detail
        return exc.code, parsed


def test_builder_custom_agent_full_flow() -> None:
    slug = f"pytest-agent-{int(time.time())}"
    target_id = slug.replace("-", "_")

    status, bricks = _request("GET", "/builder/bricks?type_code=role")
    assert status == 200, bricks
    role_id = bricks[0]["id"]

    status, draft = _request(
        "POST",
        "/builder/compose/custom-agents/draft",
        {
            "slug": slug,
            "name": "Pytest agent",
            "mission": "Validate builder flow",
            "owner_user_id": "user:local",
            "composition": [{"slot": "role", "brick_id": role_id, "sort_order": 0}],
        },
    )
    assert status == 201 or status == 200, draft
    custom_agent_id = draft["custom_agent_id"]
    version_id = draft["version_id"]

    status, listed = _request("GET", "/builder/compose/custom-agents?owner_user_id=user:local")
    assert status == 200, listed
    row = next((r for r in listed if r["slug"] == slug), None)
    assert row is not None
    assert row["status"] == "draft"
    assert isinstance(row.get("created_at"), str)

    status, published = _request(
        "POST",
        f"/builder/compose/custom-agents/versions/{version_id}/publish",
        {},
    )
    assert status == 200, published
    assert published["runtime_agent_id"] == f"custom-{slug}"

    status, listed_after = _request("GET", "/builder/compose/custom-agents?owner_user_id=user:local")
    assert status == 200, listed_after
    row_after = next((r for r in listed_after if r["slug"] == slug), None)
    assert row_after is not None
    assert row_after["status"] == "published"

    status, promo = _request(
        "POST",
        "/builder/promotions",
        {
            "requester_id": "user:local",
            "source_kind": "custom_agent",
            "source_id": custom_agent_id,
            "target_kind": "builder_agent",
            "target_id": target_id,
            "proposed_payload": {"domain_code": "dev"},
        },
    )
    assert status == 201, promo
    assert promo["source_id"] == custom_agent_id
    assert promo["target_id"] == target_id

    status, promo_list = _request("GET", "/builder/promotions?status=submitted")
    assert status == 200, promo_list
    assert any(p["id"] == promo["id"] for p in promo_list)

    status, approved = _request(
        "POST",
        f"/builder/promotions/{promo['id']}/approve",
        {"review_notes": "pytest"},
    )
    assert status == 200, approved
    assert approved["status"] == "approved"
    assert approved["catalog_agent_id"] == target_id
