/**
 * Client HTTP vers orchestrateur-trace-service (hors origin du backend principal).
 */

export type TraceStage =
  | "user_input"
  | "intent"
  | "context"
  | "reasoning"
  | "generation"
  | "response";

export type SpanStatus = "pending" | "ok" | "error";

export type TraceSpanDto = {
  span_id: string;
  trace_id: string;
  stage: TraceStage;
  name: string | null;
  parent_span_id: string | null;
  started_at: string;
  ended_at: string | null;
  status: SpanStatus;
  summary_in: string | null;
  summary_out: string | null;
  attributes: Record<string, unknown>;
  error_message: string | null;
};

export type TraceRecordDto = {
  trace_id: string;
  created_at: string;
  conversation_id: string | null;
  metadata: Record<string, unknown>;
  spans: TraceSpanDto[];
};

export type TraceSummaryDto = {
  trace_id: string;
  created_at: string;
  conversation_id: string | null;
  metadata: Record<string, unknown>;
};

export type ConversationTracesDto = {
  conversation_id: string;
  traces: TraceSummaryDto[];
};

export const TRACE_META_USER_TEXT = "user_text";
export const TRACE_META_ASSISTANT_TEXT = "assistant_text";
export const TRACE_META_CONTEXT_MODE = "context_mode";
export const TRACE_META_HISTORY_MESSAGES = "history_messages";
export const TRACE_META_HISTORY_CHARS = "history_chars";

export const traceServiceBaseUrl: string =
  import.meta.env.VITE_TRACE_SERVICE_URL ?? "http://127.0.0.1:8090";

async function ensureOk(response: Response, path: string): Promise<void> {
  if (response.ok) {
    return;
  }
  let detail = response.statusText;
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) {
      detail = body.detail;
    }
  } catch {
    /* ignore */
  }
  throw new Error(`${path}: ${detail}`);
}

export async function fetchTraceServiceHealth(): Promise<{ status: string }> {
  const url = new URL("/health", traceServiceBaseUrl).toString();
  const response = await fetch(url);
  await ensureOk(response, "/health");
  return response.json() as Promise<{ status: string }>;
}

export async function createTrace(body: {
  conversation_id?: string | null;
  metadata?: Record<string, unknown>;
}): Promise<{ trace_id: string; created_at: string }> {
  const url = new URL("/v1/traces", traceServiceBaseUrl).toString();
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await ensureOk(response, "POST /v1/traces");
  return response.json() as Promise<{ trace_id: string; created_at: string }>;
}

export async function startTraceSpan(
  traceId: string,
  body: {
    stage: TraceStage;
    name?: string | null;
    parent_span_id?: string | null;
    summary_in?: string | null;
    attributes?: Record<string, unknown>;
  },
): Promise<{ span_id: string; trace_id: string; started_at: string }> {
  const url = new URL(`/v1/traces/${traceId}/spans`, traceServiceBaseUrl).toString();
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await ensureOk(response, "POST /v1/traces/.../spans");
  return response.json() as Promise<{ span_id: string; trace_id: string; started_at: string }>;
}

export async function patchTraceSpan(
  traceId: string,
  spanId: string,
  body: {
    status?: SpanStatus;
    summary_out?: string | null;
    summary_in?: string | null;
    attributes?: Record<string, unknown> | null;
    error_message?: string | null;
  },
): Promise<void> {
  const url = new URL(
    `/v1/traces/${traceId}/spans/${spanId}`,
    traceServiceBaseUrl,
  ).toString();
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await ensureOk(response, "PATCH /v1/traces/.../spans/...");
}

export async function fetchTrace(traceId: string): Promise<TraceRecordDto> {
  const url = new URL(`/v1/traces/${traceId}`, traceServiceBaseUrl).toString();
  const response = await fetch(url);
  await ensureOk(response, "GET /v1/traces/...");
  return response.json() as Promise<TraceRecordDto>;
}

export async function fetchConversationTraces(
  conversationId: string,
  limit = 100,
): Promise<ConversationTracesDto> {
  const url = new URL(
    `/v1/conversations/${encodeURIComponent(conversationId)}/traces`,
    traceServiceBaseUrl,
  );
  url.searchParams.set("limit", String(limit));
  const response = await fetch(url.toString());
  await ensureOk(response, "GET /v1/conversations/.../traces");
  return response.json() as Promise<ConversationTracesDto>;
}

export async function patchTraceMetadata(
  traceId: string,
  metadata: Record<string, unknown>,
): Promise<TraceRecordDto> {
  const url = new URL(`/v1/traces/${traceId}`, traceServiceBaseUrl).toString();
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ metadata }),
  });
  await ensureOk(response, "PATCH /v1/traces/...");
  return response.json() as Promise<TraceRecordDto>;
}
