from __future__ import annotations

import os
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from orchestrateur_trace.models import (
    ConversationTracesResponse,
    SpanPatch,
    SpanStart,
    SpanStartResponse,
    TraceCreate,
    TraceCreateResponse,
    TraceMetadataPatch,
    TraceRecord,
)
from orchestrateur_trace.sqlite_store import SqliteTraceStore
from orchestrateur_trace.store import TraceStore

_sqlite_path = os.getenv("TRACE_SQLITE_PATH", "").strip()
if _sqlite_path:
    store = SqliteTraceStore(_sqlite_path)
else:
    store = TraceStore()

app = FastAPI(
    title="Orchestrateur — service de traces conversationnelles",
    version="0.1.0",
    description="Enregistrement de spans par phase (entrée → intention → contexte → raisonnement → génération → réponse).",
)

# Navigateur (UI Ionic) : origines par défaut localhost / 127.0.0.1 port 3000 (et dev Vite 5173).
_default_origins = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:5173,http://127.0.0.1:5173"
)
_origins_raw = os.getenv("TRACE_CORS_ORIGINS", _default_origins)
_cors_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/traces", response_model=TraceCreateResponse)
def create_trace(body: TraceCreate) -> TraceCreateResponse:
    rec = store.create_trace(body)
    return TraceCreateResponse(trace_id=rec.trace_id, created_at=rec.created_at)


@app.get("/v1/traces/{trace_id}", response_model=TraceRecord)
def get_trace(trace_id: UUID) -> TraceRecord:
    rec = store.get_trace(trace_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return rec


@app.get("/v1/conversations/{conversation_id}/traces", response_model=ConversationTracesResponse)
def list_conversation_traces(
    conversation_id: str,
    limit: int = 100,
) -> ConversationTracesResponse:
    traces = store.list_traces_by_conversation(conversation_id, limit=limit)
    return ConversationTracesResponse(conversation_id=conversation_id, traces=traces)


@app.patch("/v1/traces/{trace_id}", response_model=TraceRecord)
def patch_trace_metadata(trace_id: UUID, body: TraceMetadataPatch) -> TraceRecord:
    rec = store.update_trace_metadata(trace_id, dict(body.metadata))
    if rec is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return rec


@app.post("/v1/traces/{trace_id}/spans", response_model=SpanStartResponse)
def start_span(trace_id: UUID, body: SpanStart) -> SpanStartResponse:
    sp = store.start_span(trace_id, body)
    if sp is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return SpanStartResponse(span_id=sp.span_id, trace_id=sp.trace_id, started_at=sp.started_at)


@app.patch("/v1/traces/{trace_id}/spans/{span_id}")
def patch_span(trace_id: UUID, span_id: UUID, body: SpanPatch) -> dict[str, str]:
    updated = store.patch_span(trace_id, span_id, body)
    if updated is None:
        raise HTTPException(status_code=404, detail="trace or span not found")
    return {"status": "updated", "span_id": str(updated.span_id)}
