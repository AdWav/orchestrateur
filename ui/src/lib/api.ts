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
    throw new Error(`HTTP ${response.status} sur ${path}`);
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
    throw new Error(`HTTP ${response.status} sur ${path}`);
  }

  return (await response.json()) as TResponse;
}

export function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export function fetchServiceStatus(): Promise<ServiceMeshStatusResponse> {
  return fetchJson<ServiceMeshStatusResponse>("/v1/services/status");
}

export function fetchTeam(): Promise<TeamSpecification> {
  return fetchJson<TeamSpecification>("/v1/team");
}

export function fetchUseCases(): Promise<UseCaseDefinition[]> {
  return fetchJson<UseCaseDefinition[]>("/v1/use-cases");
}

export function runRepoAudit(
  body: RepoAuditWorkflowRequest,
): Promise<RepoAuditReport> {
  return postJson<RepoAuditWorkflowRequest, RepoAuditReport>(
    "/v1/workflows/repo-audit",
    body,
  );
}
