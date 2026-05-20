import { apiBaseUrl } from "./api";

export type BuilderBrickSummary = {
  id: number;
  slug: string;
  label: string;
  description: string | null;
  status: string;
  source: string;
  type_code: string;
  domain_code: string | null;
};

export type BuilderCatalogAgent = {
  id: string;
  domain_id: number | null;
  published_version: string | null;
};

export type BuilderCustomAgentSummary = {
  id: string;
  slug: string;
  workspace_id: string | null;
  owner_user_id: string;
  version_id: number | null;
  version: string | null;
  status: string | null;
  created_at: string | null;
};

export type BuilderCompositionItem = {
  slot: string;
  brick_id: number;
  sort_order?: number;
};

export type BuilderDraftResponse = {
  custom_agent_id?: string;
  version_id: number;
  version: string;
  status: string;
};

export type BuilderPublishResponse = {
  custom_agent_id?: string;
  version_id: number;
  version: string;
  status: string;
  runtime_agent_id?: string | null;
};

export type BuilderPromotionSubmitBody = {
  requester_id: string;
  source_kind: string;
  source_id: string;
  target_kind: string;
  proposed_payload: Record<string, unknown>;
  target_id?: string | null;
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(new URL(path, apiBaseUrl).toString(), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status} ${path}`);
  }
  return (await response.json()) as T;
}

async function postJson<TBody, TResponse>(path: string, body: TBody): Promise<TResponse> {
  const response = await fetch(new URL(path, apiBaseUrl).toString(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status} ${path}`);
  }
  return (await response.json()) as TResponse;
}

export async function fetchBuilderHealth(): Promise<{ status: string }> {
  return fetchJson("/health");
}

export async function fetchBuilderBricks(params?: {
  type_code?: string;
  domain_code?: string;
}): Promise<BuilderBrickSummary[]> {
  const url = new URL("/builder/bricks", apiBaseUrl);
  if (params?.type_code) {
    url.searchParams.set("type_code", params.type_code);
  }
  if (params?.domain_code) {
    url.searchParams.set("domain_code", params.domain_code);
  }
  const response = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} /builder/bricks`);
  }
  return (await response.json()) as BuilderBrickSummary[];
}

export async function fetchBuilderCatalogAgents(): Promise<BuilderCatalogAgent[]> {
  return fetchJson("/builder/catalog/agents");
}

export async function fetchCustomAgents(
  ownerUserId?: string,
): Promise<BuilderCustomAgentSummary[]> {
  const url = new URL("/builder/compose/custom-agents", apiBaseUrl);
  if (ownerUserId) {
    url.searchParams.set("owner_user_id", ownerUserId);
  }
  const response = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} /builder/compose/custom-agents`);
  }
  return (await response.json()) as BuilderCustomAgentSummary[];
}

export async function createCustomAgentDraft(body: {
  slug: string;
  name: string;
  mission: string;
  owner_user_id: string;
  composition: BuilderCompositionItem[];
  runner_role?: string | null;
  business_role?: string | null;
}): Promise<BuilderDraftResponse> {
  return postJson("/builder/compose/custom-agents/draft", body);
}

export async function publishCustomAgentVersion(
  versionId: number,
): Promise<BuilderPublishResponse> {
  return postJson(`/builder/compose/custom-agents/versions/${versionId}/publish`, {});
}

export type BuilderPromotion = {
  id: number;
  requester_id: string;
  source_kind: string;
  source_id: string;
  target_kind: string;
  target_id: string | null;
  proposed_payload: Record<string, unknown> | null;
  status: string;
  catalog_agent_id?: string | null;
  catalog_version_id?: number | null;
  reviewer_id?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
};

export type BuilderPromotionReviewBody = {
  review_notes?: string | null;
};

export async function fetchBuilderPromotions(
  status?: string,
): Promise<BuilderPromotion[]> {
  const url = new URL("/builder/promotions", apiBaseUrl);
  if (status) {
    url.searchParams.set("status", status);
  }
  const response = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} /builder/promotions`);
  }
  return (await response.json()) as BuilderPromotion[];
}

export async function submitBuilderPromotion(
  body: BuilderPromotionSubmitBody,
): Promise<{ id: number; status: string }> {
  return postJson("/builder/promotions", body);
}

export async function approveBuilderPromotion(
  requestId: number,
  body: BuilderPromotionReviewBody = {},
): Promise<BuilderPromotion> {
  return postJson(`/builder/promotions/${requestId}/approve`, body);
}

export async function rejectBuilderPromotion(
  requestId: number,
  body: BuilderPromotionReviewBody = {},
): Promise<BuilderPromotion> {
  return postJson(`/builder/promotions/${requestId}/reject`, body);
}
