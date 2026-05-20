from __future__ import annotations

import pytest

from core.builder.compose import runtime_id_for_custom_agent, runtime_id_for_custom_workflow
from core.contracts import AgentDefinition


def test_runtime_id_for_custom_agent() -> None:
    agent_id = runtime_id_for_custom_agent("Mon Agent Test")
    AgentDefinition.model_validate(
        {
            "id": agent_id,
            "name": "Test",
            "business_role": "Dev",
            "mission": "Mission",
        }
    )


def test_runtime_id_for_custom_workflow() -> None:
    workflow_id = runtime_id_for_custom_workflow("Team TDD")
    assert workflow_id.startswith("custom-wf-")
    assert len(workflow_id) <= 63


def test_runtime_id_empty_slug_fallback() -> None:
    assert runtime_id_for_custom_agent("!!!") == "custom-item"
