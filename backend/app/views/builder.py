from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import get_container
from app.models.api_schemas import (
    BuilderAgentDraftRequest,
    BuilderAuditEventResponse,
    BuilderBrickDetailResponse,
    BuilderBrickSummaryResponse,
    BuilderCatalogAgentResponse,
    BuilderCatalogAgentVersionResponse,
    BuilderCatalogWorkflowResponse,
    BuilderCreateBrickRequest,
    BuilderCustomAgentDraftRequest,
    BuilderCustomAgentSummaryResponse,
    BuilderCustomWorkflowDraftRequest,
    BuilderCustomWorkflowSummaryResponse,
    BuilderDraftResponse,
    BuilderPendingAgentCreateRequest,
    BuilderPendingAgentResponse,
    BuilderPendingBrickCreateRequest,
    BuilderPendingBrickResponse,
    BuilderPendingDecisionResponse,
    BuilderPromotionResponse,
    BuilderPromotionReviewRequest,
    BuilderPromotionSubmitRequest,
    BuilderPublishResponse,
    BuilderSessionCreateRequest,
    BuilderSessionDetailResponse,
    BuilderSessionResponse,
    BuilderWorkflowDraftRequest,
)

router = APIRouter(prefix="/builder", tags=["builder"])


@router.get("/bricks", response_model=list[BuilderBrickSummaryResponse])
def list_bricks(
    type_code: str | None = Query(default=None),
    domain_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[BuilderBrickSummaryResponse]:
    rows = get_container().builder_controller.list_bricks(
        type_code=type_code,
        domain_code=domain_code,
        status=status,
    )
    return [BuilderBrickSummaryResponse.model_validate(row) for row in rows]


@router.post("/bricks", response_model=BuilderBrickDetailResponse, status_code=status.HTTP_201_CREATED)
def create_brick(body: BuilderCreateBrickRequest) -> BuilderBrickDetailResponse:
    try:
        row = get_container().builder_controller.create_brick(
            type_code=body.type_code,
            label=body.label,
            domain_code=body.domain_code,
            description=body.description,
            slug=body.slug,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderBrickDetailResponse.model_validate(row)


@router.get("/bricks/{brick_id}", response_model=BuilderBrickDetailResponse)
def get_brick(brick_id: int) -> BuilderBrickDetailResponse:
    try:
        row = get_container().builder_controller.get_brick(brick_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BuilderBrickDetailResponse.model_validate(row)


@router.get("/catalog/agents", response_model=list[BuilderCatalogAgentResponse])
def list_catalog_agents() -> list[BuilderCatalogAgentResponse]:
    rows = get_container().builder_controller.list_catalog_agents()
    return [BuilderCatalogAgentResponse.model_validate(row) for row in rows]


@router.get("/catalog/workflows", response_model=list[BuilderCatalogWorkflowResponse])
def list_catalog_workflows() -> list[BuilderCatalogWorkflowResponse]:
    rows = get_container().builder_controller.list_catalog_workflows()
    return [BuilderCatalogWorkflowResponse.model_validate(row) for row in rows]


@router.get(
    "/catalog/agents/{agent_id}/versions",
    response_model=list[BuilderCatalogAgentVersionResponse],
)
def list_agent_versions(agent_id: str) -> list[BuilderCatalogAgentVersionResponse]:
    rows = get_container().builder_controller.list_agent_versions(agent_id)
    return [BuilderCatalogAgentVersionResponse.model_validate(row) for row in rows]


@router.post(
    "/compose/agents/draft",
    response_model=BuilderDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_draft(body: BuilderAgentDraftRequest) -> BuilderDraftResponse:
    try:
        result = get_container().builder_controller.create_agent_draft(
            agent_id=body.agent_id,
            name=body.name,
            mission=body.mission,
            composition=[item.model_dump() for item in body.composition],
            domain_code=body.domain_code,
            runner_role=body.runner_role,
            business_role=body.business_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderDraftResponse.model_validate(result)


@router.post(
    "/compose/agents/versions/{version_id}/publish",
    response_model=BuilderPublishResponse,
)
def publish_agent_version(version_id: int) -> BuilderPublishResponse:
    try:
        result = get_container().builder_controller.publish_agent_version(version_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPublishResponse.model_validate(result)


@router.post(
    "/compose/workflows/draft",
    response_model=BuilderDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_draft(body: BuilderWorkflowDraftRequest) -> BuilderDraftResponse:
    try:
        result = get_container().builder_controller.create_workflow_draft(
            workflow_id=body.workflow_id,
            name=body.name,
            goal=body.goal,
            steps=[step.model_dump() for step in body.steps],
            context=body.context,
            constraints=body.constraints,
            success_criteria=body.success_criteria,
            domain_code=body.domain_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderDraftResponse.model_validate(result)


@router.post(
    "/compose/workflows/versions/{version_id}/publish",
    response_model=BuilderPublishResponse,
)
def publish_workflow_version(version_id: int) -> BuilderPublishResponse:
    try:
        result = get_container().builder_controller.publish_workflow_version(version_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPublishResponse.model_validate(result)


@router.post(
    "/compose/custom-agents/draft",
    response_model=BuilderDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_custom_agent_draft(body: BuilderCustomAgentDraftRequest) -> BuilderDraftResponse:
    result = get_container().builder_controller.create_custom_agent_draft(
        slug=body.slug,
        name=body.name,
        mission=body.mission,
        composition=[item.model_dump() for item in body.composition],
        owner_user_id=body.owner_user_id,
        workspace_id=body.workspace_id,
        runner_role=body.runner_role,
        business_role=body.business_role,
    )
    return BuilderDraftResponse.model_validate(result)


@router.get("/compose/custom-agents", response_model=list[BuilderCustomAgentSummaryResponse])
def list_custom_agents(
    owner_user_id: str | None = Query(default=None),
) -> list[BuilderCustomAgentSummaryResponse]:
    rows = get_container().builder_controller.list_custom_agents(owner_user_id=owner_user_id)
    return [BuilderCustomAgentSummaryResponse.model_validate(row) for row in rows]


@router.get("/pending/bricks", response_model=list[BuilderPendingBrickResponse])
def list_pending_bricks() -> list[BuilderPendingBrickResponse]:
    rows = get_container().builder_controller.list_pending_brick_proposals()
    return [BuilderPendingBrickResponse.model_validate(row) for row in rows]


@router.post(
    "/pending/bricks",
    response_model=BuilderPendingDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pending_brick(body: BuilderPendingBrickCreateRequest) -> BuilderPendingDecisionResponse:
    try:
        result = get_container().builder_controller.create_pending_brick_proposal(
            field_path=body.field_path,
            proposed_value=body.proposed_value,
            target_brick_id=body.target_brick_id,
            type_code=body.type_code,
            session_id=body.session_id,
            proposed_by=body.proposed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderPendingDecisionResponse.model_validate(result)


@router.post(
    "/pending/bricks/{proposal_id}/approve",
    response_model=BuilderPendingDecisionResponse,
)
def approve_pending_brick(proposal_id: int) -> BuilderPendingDecisionResponse:
    try:
        result = get_container().builder_controller.approve_pending_brick(proposal_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPendingDecisionResponse.model_validate(result)


@router.post(
    "/pending/bricks/{proposal_id}/reject",
    response_model=BuilderPendingDecisionResponse,
)
def reject_pending_brick(proposal_id: int) -> BuilderPendingDecisionResponse:
    try:
        result = get_container().builder_controller.reject_pending_brick(proposal_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BuilderPendingDecisionResponse.model_validate(result)


@router.post(
    "/compose/custom-agents/versions/{version_id}/publish",
    response_model=BuilderPublishResponse,
)
def publish_custom_agent_version(version_id: int) -> BuilderPublishResponse:
    try:
        result = get_container().builder_controller.publish_custom_agent_version(version_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPublishResponse.model_validate(result)


@router.post(
    "/compose/custom-workflows/draft",
    response_model=BuilderDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_custom_workflow_draft(body: BuilderCustomWorkflowDraftRequest) -> BuilderDraftResponse:
    try:
        result = get_container().builder_controller.create_custom_workflow_draft(
            slug=body.slug,
            name=body.name,
            goal=body.goal,
            steps=[step.model_dump() for step in body.steps],
            owner_user_id=body.owner_user_id,
            workspace_id=body.workspace_id,
            context=body.context,
            constraints=body.constraints,
            success_criteria=body.success_criteria,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderDraftResponse.model_validate(result)


@router.post(
    "/compose/custom-workflows/versions/{version_id}/publish",
    response_model=BuilderPublishResponse,
)
def publish_custom_workflow_version(version_id: int) -> BuilderPublishResponse:
    try:
        result = get_container().builder_controller.publish_custom_workflow_version(version_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPublishResponse.model_validate(result)


@router.get(
    "/compose/custom-workflows",
    response_model=list[BuilderCustomWorkflowSummaryResponse],
)
def list_custom_workflows(
    owner_user_id: str | None = Query(default=None),
) -> list[BuilderCustomWorkflowSummaryResponse]:
    rows = get_container().builder_controller.list_custom_workflows(owner_user_id=owner_user_id)
    return [BuilderCustomWorkflowSummaryResponse.model_validate(row) for row in rows]


@router.get("/pending/agents", response_model=list[BuilderPendingAgentResponse])
def list_pending_agents(
    draft_version_id: int | None = Query(default=None),
) -> list[BuilderPendingAgentResponse]:
    rows = get_container().builder_controller.list_pending_agent_proposals(
        draft_version_id=draft_version_id,
    )
    return [BuilderPendingAgentResponse.model_validate(row) for row in rows]


@router.post(
    "/pending/agents",
    response_model=BuilderPendingDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pending_agent(body: BuilderPendingAgentCreateRequest) -> BuilderPendingDecisionResponse:
    try:
        result = get_container().builder_controller.create_pending_agent_proposal(
            draft_version_id=body.draft_version_id,
            field_path=body.field_path,
            proposed_value=body.proposed_value,
            session_id=body.session_id,
            proposed_by=body.proposed_by,
        )
    except (KeyError, ValueError) as exc:
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, KeyError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return BuilderPendingDecisionResponse.model_validate(result)


@router.post(
    "/pending/agents/{proposal_id}/approve",
    response_model=BuilderPendingDecisionResponse,
)
def approve_pending_agent(proposal_id: int) -> BuilderPendingDecisionResponse:
    try:
        result = get_container().builder_controller.approve_pending_agent(proposal_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPendingDecisionResponse.model_validate(result)


@router.post(
    "/pending/agents/{proposal_id}/reject",
    response_model=BuilderPendingDecisionResponse,
)
def reject_pending_agent(proposal_id: int) -> BuilderPendingDecisionResponse:
    try:
        result = get_container().builder_controller.reject_pending_agent(proposal_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BuilderPendingDecisionResponse.model_validate(result)


@router.get("/promotions", response_model=list[BuilderPromotionResponse])
def list_promotions(
    status: str | None = Query(default=None),
) -> list[BuilderPromotionResponse]:
    rows = get_container().builder_controller.list_promotions(status=status)
    return [BuilderPromotionResponse.model_validate(row) for row in rows]


@router.post(
    "/promotions",
    response_model=BuilderPromotionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_promotion(body: BuilderPromotionSubmitRequest) -> BuilderPromotionResponse:
    try:
        result = get_container().builder_controller.submit_promotion(
            requester_id=body.requester_id,
            source_kind=body.source_kind,
            source_id=body.source_id,
            target_kind=body.target_kind,
            proposed_payload=body.proposed_payload,
            target_id=body.target_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderPromotionResponse.model_validate(result)


@router.post(
    "/promotions/{request_id}/approve",
    response_model=BuilderPromotionResponse,
)
def approve_promotion(
    request_id: int,
    body: BuilderPromotionReviewRequest | None = None,
) -> BuilderPromotionResponse:
    notes = body.review_notes if body else None
    try:
        result = get_container().builder_controller.approve_promotion(
            request_id,
            review_notes=notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BuilderPromotionResponse.model_validate(result)


@router.post(
    "/promotions/{request_id}/reject",
    response_model=BuilderPromotionResponse,
)
def reject_promotion(
    request_id: int,
    body: BuilderPromotionReviewRequest | None = None,
) -> BuilderPromotionResponse:
    notes = body.review_notes if body else None
    try:
        result = get_container().builder_controller.reject_promotion(
            request_id,
            review_notes=notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BuilderPromotionResponse.model_validate(result)


@router.post(
    "/sessions",
    response_model=BuilderSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(body: BuilderSessionCreateRequest) -> BuilderSessionResponse:
    try:
        result = get_container().builder_controller.create_session(
            kind=body.kind,
            actor_type=body.actor_type,
            actor_id=body.actor_id,
            goal_prompt=body.goal_prompt,
            session_id=body.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BuilderSessionResponse.model_validate(result)


@router.get("/sessions/{session_id}", response_model=BuilderSessionDetailResponse)
def get_session(session_id: str) -> BuilderSessionDetailResponse:
    try:
        result = get_container().builder_controller.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BuilderSessionDetailResponse(
        session=BuilderSessionResponse.model_validate(result["session"]),
        inputs=result["inputs"],
        outputs=result["outputs"],
        audit_events=[
            BuilderAuditEventResponse.model_validate(row) for row in result["audit_events"]
        ],
    )


@router.get("/audit", response_model=list[BuilderAuditEventResponse])
def list_audit_events(
    entity_type: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[BuilderAuditEventResponse]:
    rows = get_container().builder_controller.list_audit_events(
        entity_type=entity_type,
        session_id=session_id,
        limit=limit,
    )
    return [BuilderAuditEventResponse.model_validate(row) for row in rows]
