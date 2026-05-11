export type HealthResponse = {
  status: string;
  service: string;
};

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

export function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export function fetchTeam(): Promise<TeamSpecification> {
  return fetchJson<TeamSpecification>("/v1/team");
}

export function fetchUseCases(): Promise<UseCaseDefinition[]> {
  return fetchJson<UseCaseDefinition[]>("/v1/use-cases");
}
