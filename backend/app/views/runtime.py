from __future__ import annotations

from fastapi import APIRouter

from app.controllers import runtime_controller
from app.models.api_schemas import RuntimeRecommendationRequest
from serve.local_runtime import RuntimeRecommendation

router = APIRouter(tags=["runtime"])


@router.post("/runtime/recommendation", response_model=RuntimeRecommendation)
def runtime_recommendation(request: RuntimeRecommendationRequest) -> RuntimeRecommendation:
    return runtime_controller.runtime_recommendation(request)
