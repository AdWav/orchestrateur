from __future__ import annotations

from threading import Lock
from uuid import UUID

from orchestrateur_trace.models import (
    SpanPatch,
    SpanRecord,
    SpanStart,
    SpanStatus,
    TraceCreate,
    TraceRecord,
    TraceSummary,
    new_span_id,
    new_trace_id,
    utc_now,
)


class TraceStore:
    """Stockage MVP en mémoire (thread-safe)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._traces: dict[UUID, TraceRecord] = {}

    def create_trace(self, body: TraceCreate) -> TraceRecord:
        tid = new_trace_id()
        now = utc_now()
        rec = TraceRecord(
            trace_id=tid,
            created_at=now,
            conversation_id=body.conversation_id,
            metadata=dict(body.metadata),
            spans=[],
        )
        with self._lock:
            self._traces[tid] = rec
        return rec

    def get_trace(self, trace_id: UUID) -> TraceRecord | None:
        with self._lock:
            t = self._traces.get(trace_id)
            if t is None:
                return None
            return t.model_copy(deep=True)

    def start_span(self, trace_id: UUID, body: SpanStart) -> SpanRecord | None:
        now = utc_now()
        span = SpanRecord(
            span_id=new_span_id(),
            trace_id=trace_id,
            stage=body.stage,
            name=body.name,
            parent_span_id=body.parent_span_id,
            started_at=now,
            status=SpanStatus.PENDING,
            summary_in=body.summary_in,
            attributes=dict(body.attributes),
        )
        with self._lock:
            tr = self._traces.get(trace_id)
            if tr is None:
                return None
            tr.spans.append(span)
        return span

    def patch_span(
        self,
        trace_id: UUID,
        span_id: UUID,
        body: SpanPatch,
    ) -> SpanRecord | None:
        with self._lock:
            tr = self._traces.get(trace_id)
            if tr is None:
                return None
            for i, sp in enumerate(tr.spans):
                if sp.span_id == span_id:
                    ended = body.ended_at or utc_now()
                    attrs = dict(sp.attributes)
                    if body.attributes:
                        attrs.update(body.attributes)
                    updated = sp.model_copy(
                        update={
                            "ended_at": ended,
                            "status": body.status or sp.status,
                            "summary_out": body.summary_out if body.summary_out is not None else sp.summary_out,
                            "attributes": attrs,
                            "error_message": body.error_message if body.error_message is not None else sp.error_message,
                        }
                    )
                    tr.spans[i] = updated
                    return updated
        return None

    def update_trace_metadata(self, trace_id: UUID, metadata: dict) -> TraceRecord | None:
        with self._lock:
            tr = self._traces.get(trace_id)
            if tr is None:
                return None
            merged = dict(tr.metadata)
            merged.update(metadata)
            tr.metadata = merged
            return tr.model_copy(deep=True)

    def list_traces_by_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
    ) -> list[TraceSummary]:
        with self._lock:
            items = [
                t
                for t in self._traces.values()
                if t.conversation_id == conversation_id
            ]
            items.sort(key=lambda t: t.created_at)
            items = items[-limit:]
            return [
                TraceSummary(
                    trace_id=t.trace_id,
                    created_at=t.created_at,
                    conversation_id=t.conversation_id,
                    metadata=dict(t.metadata),
                )
                for t in items
            ]
