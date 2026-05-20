from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TraceStage(StrEnum):
    """Phases du parcours utilisateur (aligné docs/conversation-trace-service.md)."""

    USER_INPUT = "user_input"
    INTENT = "intent"
    CONTEXT = "context"
    REASONING = "reasoning"
    GENERATION = "generation"
    RESPONSE = "response"


class SpanStatus(StrEnum):
    PENDING = "pending"
    OK = "ok"
    ERROR = "error"


class TraceCreate(BaseModel):
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    trace_id: UUID
    created_at: datetime
    conversation_id: str | None
    metadata: dict[str, Any]
    spans: list["SpanRecord"] = Field(default_factory=list)


class SpanStart(BaseModel):
    stage: TraceStage
    name: str | None = None
    parent_span_id: UUID | None = None
    summary_in: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class SpanPatch(BaseModel):
    ended_at: datetime | None = None
    status: SpanStatus | None = None
    summary_out: str | None = None
    attributes: dict[str, Any] | None = None
    error_message: str | None = None


class SpanRecord(BaseModel):
    span_id: UUID
    trace_id: UUID
    stage: TraceStage
    name: str | None
    parent_span_id: UUID | None
    started_at: datetime
    ended_at: datetime | None = None
    status: SpanStatus = SpanStatus.PENDING
    summary_in: str | None = None
    summary_out: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class SpanStartResponse(BaseModel):
    span_id: UUID
    trace_id: UUID
    started_at: datetime


class TraceCreateResponse(BaseModel):
    trace_id: UUID
    created_at: datetime


def new_trace_id() -> UUID:
    return uuid4()


def new_span_id() -> UUID:
    return uuid4()
