import { getActiveTranslator } from "../i18n/core";

export type HealthResponse = {
  status: string;
  service: string;
};

export type ServiceStatus = {
  key: string;
  label: string;
  target: string;
  port: string | null;
  active: boolean;
};

export type ServiceMeshStatusResponse = {
  services: ServiceStatus[];
};

export type OllamaModelsResponse = {
  models: string[];
};

export type ModelWarmUnloadAck = {
  model: string;
  action: "warm" | "unload";
};

export type OllamaRuntimeSettings = {
  default_model: string;
  runner_models: Record<string, string>;
  pipeline_steps: string[];
  settings_persist_path: string | null;
  ollama_routing_active: boolean;
};

export type SamplingProfile = {
  temperature: number | null;
  top_k: number | null;
  top_p: number | null;
  min_p: number | null;
  mirostat: number | null;
  mirostat_eta: number | null;
  mirostat_tau: number | null;
  presence_penalty: number | null;
  frequency_penalty: number | null;
  repeat_penalty: number | null;
  repeat_last_n: number | null;
  logit_bias: Record<string, number> | null;
  stop: string[] | null;
  num_predict: number | null;
};

export type SamplingSettingsResponse = {
  orchestration: SamplingProfile;
  live: SamplingProfile;
  settings_persist_path: string | null;
  ollama_active: boolean;
};

export type SamplingLiveUpdate = SamplingProfile;

export type SamplingPreviewRequest = {
  prompt: string;
  model?: string | null;
};

export type SamplingPreviewResponse = {
  model: string;
  profile: "live";
  content: string;
  backend: string;
};

export type SamplingPreviewStreamStats = {
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
};

export type SamplingPreviewStreamEvent =
  | { event: "token"; content: string }
  | {
      event: "done";
      model: string;
      profile: "live";
      backend: string;
      content: string;
      stats: SamplingPreviewStreamStats;
    }
  | { event: "error"; detail: string };

export type ModelTokenPiece = {
  id: number;
  text: string;
};

export type SamplingTokenizeRequest = {
  text: string;
  model?: string | null;
};

export type SamplingTokenizeResponse = {
  model: string;
  source: "ollama" | "llama_cpp";
  token_count: number;
  tokens: ModelTokenPiece[];
};

export type SamplingTokenizeCapabilitiesResponse = {
  ollama_api: boolean;
  llama_cpp: boolean;
  source: "ollama" | "llama_cpp" | "unavailable";
};

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };

export type AgentDescriptor = {
  role: string;
  responsibility: string;
  capabilities: string[];
  allowed_inputs: string[];
  produces: string[];
};

export type AgentDefinition = {
  id: string;
  name: string;
  business_role: string;
  mission: string;
  capabilities: string[];
  inputs: string[];
  outputs: string[];
  guardrails: string[];
};

export type WorkflowStepDefinition = {
  id: string;
  name: string;
  agent_definition_id: string;
  objective: string;
  expected_deliverables: string[];
  success_criteria: string[];
  depends_on: string[];
};

export type WorkflowDefinition = {
  id: string;
  name: string;
  goal: string;
  context: Record<string, string>;
  constraints: string[];
  success_criteria: string[];
  steps: WorkflowStepDefinition[];
};

export type TeamSpecification = {
  id: string;
  name: string;
  purpose: string;
  methodology: string | null;
  use_case_ids: string[];
  pipeline_step_ids: string[];
  roles: AgentDescriptor[];
  handoff_contracts: string[];
  guardrails: string[];
};

export type WorkspaceInfo = {
  path: string;
  files: string[];
  test_command: string;
  runner_exec_command: string | null;
  tests_passed: boolean | null;
  test_output: string | null;
};

export type DevTeamBenchmarkRequest = {
  objective: string;
  context?: Record<string, string>;
  constraints?: string[];
  success_criteria?: string[];
  team_order?: string[];
  materialize_workspace?: boolean;
};

export type TeamBenchmarkComparison = {
  fastest_team_id: string | null;
  success_by_team: Record<string, boolean>;
  duration_ms_by_team: Record<string, number>;
  winner_by_success: string[];
  notes: string[];
};

export type DevTeamBenchmarkReport = {
  request: WorkflowRun["request"];
  team_order: string[];
  runs: WorkflowRun[];
  comparison: TeamBenchmarkComparison;
  workspace_run_id: string | null;
  workspace_root: string | null;
};

export type UseCaseDefinition = {
  id: string;
  title: string;
  description: string;
  primary_outcome: string;
  inputs: string[];
  deliverables: string[];
};

export type AgentOutput = {
  role: string;
  summary: string;
  artifacts: Record<string, JsonValue>;
  next_actions: string[];
  approved: boolean | null;
};

export type WorkflowRun = {
  request: {
    objective: string;
    context: Record<string, JsonValue>;
    constraints: string[];
    success_criteria: string[];
    expected_output: string;
    use_case_id: string | null;
  };
  outputs: AgentOutput[];
  memory: {
    state: Record<string, JsonValue>;
    events: MemoryEvent[];
  };
  verification_passed: boolean;
  team_id?: string | null;
  total_duration_ms?: number | null;
  workspace?: WorkspaceInfo | null;
};

export type MemoryEvent = {
  type: string;
  role: string;
  key?: string;
  message?: string;
  data?: Record<string, JsonValue>;
};

export type RepoInventory = {
  root_path: string;
  total_files_scanned: number;
  top_level_entries: string[];
  detected_languages: string[];
  important_files: string[];
  scanned_paths: string[];
  truncated: boolean;
};

export type EvidenceRef = {
  path: string;
  kind: string;
  reason: string;
  excerpt?: string;
  line_start?: number;
  line_end?: number;
};

export type Finding = {
  id: string;
  category: string;
  severity: string;
  title: string;
  summary: string;
  impacted_paths: string[];
  evidence_refs: EvidenceRef[];
  recommended_actions: string[];
};

export type RepoAuditValidationReport = {
  approved: boolean;
  covered_axes: string[];
  unsupported_claims: string[];
  policy_compliance: string[];
  missing_requirements: string[];
  evidence_count: number;
};

export type RepoAuditReport = {
  request: {
    objective: string;
  };
  inventory: RepoInventory | null;
  findings: Finding[];
  outputs: AgentOutput[];
  validation_report: RepoAuditValidationReport | null;
  memory: {
    state: Record<string, JsonValue>;
    events: MemoryEvent[];
  };
  verification_passed: boolean;
};

export type RepoAuditWorkflowRequest = {
  objective: string;
  repo_path: string;
  analysis_axes: string[];
};

export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(new URL(path, apiBaseUrl).toString(), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, path));
  }

  return (await response.json()) as T;
}

async function postJson<TBody, TResponse>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const response = await fetch(new URL(path, apiBaseUrl).toString(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, path));
  }

  return (await response.json()) as TResponse;
}

async function putJson<TBody, TResponse>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const response = await fetch(new URL(path, apiBaseUrl).toString(), {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, path));
  }

  return (await response.json()) as TResponse;
}

async function postJsonEmpty<T>(path: string): Promise<T> {
  const response = await fetch(new URL(path, apiBaseUrl).toString(), {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, path));
  }

  return (await response.json()) as T;
}

async function buildErrorMessage(response: Response, path: string): Promise<string> {
  const { t } = getActiveTranslator();
  const fallback = t("errors.httpFallback", { status: response.status, path });
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim().length > 0) {
      return payload.detail;
    }
  } catch {
    return fallback;
  }
  return fallback;
}

export function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export function fetchServiceStatus(): Promise<ServiceMeshStatusResponse> {
  return fetchJson<ServiceMeshStatusResponse>("/services/status");
}

export type OllamaRuntimeSettingsUpdatePayload = {
  default_model: string;
  runner_models: Record<string, string>;
};

export function fetchOllamaModels(): Promise<OllamaModelsResponse> {
  return fetchJson<OllamaModelsResponse>("/v1/runtime/ollama/models");
}

export function fetchOllamaRuntimeSettings(): Promise<OllamaRuntimeSettings> {
  return fetchJson<OllamaRuntimeSettings>("/v1/runtime/ollama/settings");
}

export function putOllamaRuntimeSettings(
  body: OllamaRuntimeSettingsUpdatePayload,
): Promise<OllamaRuntimeSettings> {
  return putJson<OllamaRuntimeSettingsUpdatePayload, OllamaRuntimeSettings>(
    "/v1/runtime/ollama/settings",
    body,
  );
}

export function fetchSamplingSettings(): Promise<SamplingSettingsResponse> {
  return fetchJson<SamplingSettingsResponse>("/v1/runtime/sampling/settings");
}

export function putLiveSamplingSettings(
  body: SamplingLiveUpdate,
): Promise<SamplingSettingsResponse> {
  return putJson<SamplingLiveUpdate, SamplingSettingsResponse>(
    "/v1/runtime/sampling/settings/live",
    body,
  );
}

export function postSamplingPreview(
  body: SamplingPreviewRequest,
): Promise<SamplingPreviewResponse> {
  return postJson<SamplingPreviewRequest, SamplingPreviewResponse>(
    "/v1/runtime/sampling/preview",
    body,
  );
}

function parseSamplingPreviewStreamLine(line: string): SamplingPreviewStreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = JSON.parse(trimmed) as SamplingPreviewStreamEvent;
  if (parsed.event === "error" && typeof parsed.detail === "string") {
    throw new Error(parsed.detail);
  }
  return parsed;
}

export function fetchSamplingTokenizeCapabilities(): Promise<SamplingTokenizeCapabilitiesResponse> {
  return fetchJson<SamplingTokenizeCapabilitiesResponse>(
    "/v1/runtime/sampling/tokenize/capabilities",
  );
}

export function postSamplingTokenize(
  body: SamplingTokenizeRequest,
): Promise<SamplingTokenizeResponse> {
  return postJson<SamplingTokenizeRequest, SamplingTokenizeResponse>(
    "/v1/runtime/sampling/tokenize",
    body,
  );
}

export async function streamSamplingPreview(
  body: SamplingPreviewRequest,
  handlers: {
    onToken: (token: string) => void;
    onDone?: (event: Extract<SamplingPreviewStreamEvent, { event: "done" }>) => void;
    signal?: AbortSignal;
  },
): Promise<void> {
  const response = await fetch(
    new URL("/v1/runtime/sampling/preview/stream", apiBaseUrl).toString(),
    {
      method: "POST",
      headers: {
        Accept: "application/x-ndjson",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: handlers.signal,
    },
  );

  if (!response.ok) {
    throw new Error(await buildErrorMessage(response, "/v1/runtime/sampling/preview/stream"));
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Streaming preview: response body unavailable.");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const event = parseSamplingPreviewStreamLine(line);
      if (!event) {
        continue;
      }
      if (event.event === "token") {
        handlers.onToken(event.content);
      } else if (event.event === "done") {
        handlers.onDone?.(event);
      }
    }
  }

  if (buffer.trim()) {
    const event = parseSamplingPreviewStreamLine(buffer);
    if (event?.event === "token") {
      handlers.onToken(event.content);
    } else if (event?.event === "done") {
      handlers.onDone?.(event);
    }
  }
}

export function postOllamaModelWarm(modelName: string): Promise<ModelWarmUnloadAck> {
  const segment = encodeURIComponent(modelName);
  return postJsonEmpty<ModelWarmUnloadAck>(`/v1/runtime/ollama/models/${segment}/warm`);
}

export function postOllamaModelUnload(modelName: string): Promise<ModelWarmUnloadAck> {
  const segment = encodeURIComponent(modelName);
  return postJsonEmpty<ModelWarmUnloadAck>(`/v1/runtime/ollama/models/${segment}/unload`);
}

export function fetchTeam(teamId?: string): Promise<TeamSpecification> {
  const query = teamId ? `?team_id=${encodeURIComponent(teamId)}` : "";
  return fetchJson<TeamSpecification>(`/team${query}`);
}

export function fetchTeams(): Promise<TeamSpecification[]> {
  return fetchJson<TeamSpecification[]>("/teams");
}

export function runDevTeamBenchmark(
  body: DevTeamBenchmarkRequest,
): Promise<DevTeamBenchmarkReport> {
  return postJson<DevTeamBenchmarkRequest, DevTeamBenchmarkReport>(
    "/workflows/dev-team-benchmark",
    body,
  );
}

export function fetchUseCases(): Promise<UseCaseDefinition[]> {
  return fetchJson<UseCaseDefinition[]>("/use-cases");
}

export function fetchAgentDefinitions(): Promise<AgentDefinition[]> {
  return fetchJson<AgentDefinition[]>("/definitions/agents");
}

export function createAgentDefinition(
  body: AgentDefinition,
): Promise<AgentDefinition> {
  return postJson<AgentDefinition, AgentDefinition>("/definitions/agents", body);
}

export function fetchWorkflowDefinitions(): Promise<WorkflowDefinition[]> {
  return fetchJson<WorkflowDefinition[]>("/definitions/workflows");
}

export function createWorkflowDefinition(
  body: WorkflowDefinition,
): Promise<WorkflowDefinition> {
  return postJson<WorkflowDefinition, WorkflowDefinition>(
    "/definitions/workflows",
    body,
  );
}

export function runRepoAudit(
  body: RepoAuditWorkflowRequest,
): Promise<RepoAuditReport> {
  return postJson<RepoAuditWorkflowRequest, RepoAuditReport>(
    "/workflows/repo-audit",
    body,
  );
}
