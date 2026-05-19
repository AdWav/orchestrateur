from __future__ import annotations

from core.dev_teams import ALL_DEV_RUNNER_STEP_IDS, DEV_PIPELINE_STEP_IDS

LEGACY_PIPELINE_STEP_IDS: tuple[str, ...] = ("plan", "research", "execute", "verify")

# Alias historique (workflows specification / repo-audit)
PIPELINE_STEP_IDS: tuple[str, ...] = LEGACY_PIPELINE_STEP_IDS

RUNNER_STEP_IDS: tuple[str, ...] = tuple(
    dict.fromkeys([*LEGACY_PIPELINE_STEP_IDS, *ALL_DEV_RUNNER_STEP_IDS])
)

LEGACY_ENGINE_ROLE_BY_STEP_ID: dict[str, str] = {
    "plan": "Planner",
    "research": "Researcher",
    "execute": "Executor",
    "verify": "Verifier",
}

DEV_ENGINE_ROLE_LABEL_BY_STEP_ID: dict[str, str] = {
    "write_tests": "TestAuthor",
    "code": "Developer",
    "code_backend": "BackendDev",
    "code_frontend": "FrontendDev",
    "api_contract": "ApiContract",
    "integration": "Integration",
    "security": "Security",
    "review": "Reviewer",
    "database": "Database",
    "devops": "DevOps",
    "run_fix": "Runner",
    "document": "TechWriter",
    "schematic": "Planner",
    "test_and_verify": "QA",
}

STEP_ID_BY_LEGACY_ENGINE_ROLE: dict[str, str] = {
    legacy: sid for sid, legacy in LEGACY_ENGINE_ROLE_BY_STEP_ID.items()
}
