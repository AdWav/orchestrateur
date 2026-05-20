from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from threading import Lock
from uuid import UUID

from orchestrateur_trace.models import (
    SpanPatch,
    SpanRecord,
    SpanStart,
    SpanStatus,
    TraceCreate,
    TraceRecord,
    TraceStage,
    TraceSummary,
    new_span_id,
    new_trace_id,
    utc_now,
)


def _dumps(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, default=str)


def _loads(s: str) -> dict:
    return json.loads(s) if s else {}


class SqliteTraceStore:
    """Persistance SQLite (fichier unique), thread-safe."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS traces (
              trace_id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              conversation_id TEXT,
              metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spans (
              span_id TEXT PRIMARY KEY,
              trace_id TEXT NOT NULL,
              idx INTEGER NOT NULL,
              stage TEXT NOT NULL,
              name TEXT,
              parent_span_id TEXT,
              started_at TEXT NOT NULL,
              ended_at TEXT,
              status TEXT NOT NULL,
              summary_in TEXT,
              summary_out TEXT,
              attributes TEXT NOT NULL,
              error_message TEXT,
              FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE,
              UNIQUE(trace_id, idx)
            );
            CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
            CREATE INDEX IF NOT EXISTS idx_traces_conversation
              ON traces(conversation_id, created_at);
            """
        )
        self._conn.commit()

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
            self._conn.execute(
                """
                INSERT INTO traces (trace_id, created_at, conversation_id, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(tid),
                    now.isoformat(),
                    body.conversation_id,
                    _dumps(dict(body.metadata)),
                ),
            )
            self._conn.commit()
        return rec

    def get_trace(self, trace_id: UUID) -> TraceRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM traces WHERE trace_id = ?", (str(trace_id),)
            ).fetchone()
            if row is None:
                return None
            span_rows = self._conn.execute(
                """
                SELECT * FROM spans WHERE trace_id = ? ORDER BY idx ASC
                """,
                (str(trace_id),),
            ).fetchall()
        spans: list[SpanRecord] = []
        for sr in span_rows:
            spans.append(SqliteTraceStore._row_to_span(sr))
        return TraceRecord(
            trace_id=UUID(row["trace_id"]),
            created_at=_parse_dt(row["created_at"]),
            conversation_id=row["conversation_id"],
            metadata=_loads(row["metadata"]),
            spans=spans,
        )

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
            cur = self._conn.execute(
                "SELECT 1 FROM traces WHERE trace_id = ?", (str(trace_id),)
            ).fetchone()
            if cur is None:
                return None
            row = self._conn.execute(
                "SELECT COALESCE(MAX(idx), -1) AS m FROM spans WHERE trace_id = ?",
                (str(trace_id),),
            ).fetchone()
            idx = int(row["m"]) + 1
            self._conn.execute(
                """
                INSERT INTO spans (
                  span_id, trace_id, idx, stage, name, parent_span_id,
                  started_at, ended_at, status, summary_in, summary_out,
                  attributes, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, ?, NULL)
                """,
                (
                    str(span.span_id),
                    str(trace_id),
                    idx,
                    span.stage.value,
                    span.name,
                    str(span.parent_span_id) if span.parent_span_id else None,
                    span.started_at.isoformat(),
                    span.status.value,
                    span.summary_in,
                    _dumps(span.attributes),
                ),
            )
            self._conn.commit()
        return span

    def patch_span(
        self,
        trace_id: UUID,
        span_id: UUID,
        body: SpanPatch,
    ) -> SpanRecord | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM spans WHERE trace_id = ? AND span_id = ?
                """,
                (str(trace_id), str(span_id)),
            ).fetchone()
            if row is None:
                return None
            sp = SqliteTraceStore._row_to_span(row)
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
            self._conn.execute(
                """
                UPDATE spans SET
                  ended_at = ?, status = ?, summary_out = ?,
                  attributes = ?, error_message = ?
                WHERE trace_id = ? AND span_id = ?
                """,
                (
                    updated.ended_at.isoformat() if updated.ended_at else None,
                    updated.status.value,
                    updated.summary_out,
                    _dumps(updated.attributes),
                    updated.error_message,
                    str(trace_id),
                    str(span_id),
                ),
            )
            self._conn.commit()
            return updated

    def update_trace_metadata(self, trace_id: UUID, metadata: dict) -> TraceRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT metadata FROM traces WHERE trace_id = ?", (str(trace_id),)
            ).fetchone()
            if row is None:
                return None
            merged = _loads(row["metadata"])
            merged.update(metadata)
            self._conn.execute(
                "UPDATE traces SET metadata = ? WHERE trace_id = ?",
                (_dumps(merged), str(trace_id)),
            )
            self._conn.commit()
        return self.get_trace(trace_id)

    def list_traces_by_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
    ) -> list[TraceSummary]:
        lim = max(1, min(limit, 500))
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT trace_id, created_at, conversation_id, metadata
                FROM traces
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (conversation_id, lim),
            ).fetchall()
        return [
            TraceSummary(
                trace_id=UUID(r["trace_id"]),
                created_at=_parse_dt(r["created_at"]),
                conversation_id=r["conversation_id"],
                metadata=_loads(r["metadata"]),
            )
            for r in rows
        ]

    @staticmethod
    def _row_to_span(sr: sqlite3.Row) -> SpanRecord:
        parent = sr["parent_span_id"]
        ended = sr["ended_at"]
        return SpanRecord(
            span_id=UUID(sr["span_id"]),
            trace_id=UUID(sr["trace_id"]),
            stage=TraceStage(sr["stage"]),
            name=sr["name"],
            parent_span_id=UUID(parent) if parent else None,
            started_at=_parse_dt(sr["started_at"]),
            ended_at=_parse_dt(ended) if ended else None,
            status=SpanStatus(sr["status"]),
            summary_in=sr["summary_in"],
            summary_out=sr["summary_out"],
            attributes=_loads(sr["attributes"]),
            error_message=sr["error_message"],
        )


def _parse_dt(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
