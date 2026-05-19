from __future__ import annotations

from app.models.api_schemas import RuntimeRecommendationRequest
from serve.local_runtime import RuntimeRecommendation, recommend_runtime


def runtime_recommendation(request: RuntimeRecommendationRequest) -> RuntimeRecommendation:
    return recommend_runtime(request.hardware, request.workload)
