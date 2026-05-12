import { getActiveI18nCopy } from "../i18n/translations";

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
  name: string;
  purpose: string;
  use_case_ids: string[];
  roles: AgentDescriptor[];
  handoff_contracts: string[];
  guardrails: string[];
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
  const fallback = getActiveI18nCopy().errors.httpFallback(response.status, path);
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
  return fetchJson<OllamaModelsResponse>("/runtime/ollama/models");
}

export function fetchOllamaRuntimeSettings(): Promise<OllamaRuntimeSettings> {
  return fetchJson<OllamaRuntimeSettings>("/runtime/ollama/settings");
}

export function putOllamaRuntimeSettings(
  body: OllamaRuntimeSettingsUpdatePayload,
): Promise<OllamaRuntimeSettings> {
  return putJson<OllamaRuntimeSettingsUpdatePayload, OllamaRuntimeSettings>(
    "/runtime/ollama/settings",
    body,
  );
}

export function postOllamaModelWarm(modelName: string): Promise<ModelWarmUnloadAck> {
  const segment = encodeURIComponent(modelName);
  return postJsonEmpty<ModelWarmUnloadAck>(`/runtime/ollama/models/${segment}/warm`);
}

export function postOllamaModelUnload(modelName: string): Promise<ModelWarmUnloadAck> {
  const segment = encodeURIComponent(modelName);
  return postJsonEmpty<ModelWarmUnloadAck>(`/runtime/ollama/models/${segment}/unload`);
}

export function fetchTeam(): Promise<TeamSpecification> {
  return fetchJson<TeamSpecification>("/team");
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
