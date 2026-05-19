import { getActiveTranslator } from "../i18n/core";
import type { JsonValue } from "./api";

export function formatJsonValue(value: JsonValue): string {
  if (value === null) {
    return getActiveTranslator().messages.common.jsonNull;
  }
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
}

const CODE_ARTIFACT_KEYS = new Set([
  "source_files",
  "backend_source_files",
  "frontend_source_files",
  "api_routes",
  "ui_components",
  "implementation_notes",
  "api_client_usage",
  "dependencies",
  "module_plan",
  "implementation_order",
  "openapi_paths",
  "schemas",
  "error_model",
  "migrations_notes",
  "architecture_notes",
  "security_findings",
  "review_comments",
]);

const TEST_ARTIFACT_KEYS = new Set([
  "test_files",
  "test_plan",
  "acceptance_criteria",
  "test_run_report",
  "tests_passed",
  "e2e_scenarios",
  "e2e_report",
]);

const DOC_ARTIFACT_KEYS = new Set([
  "documentation",
  "operator_notes",
  "delivery_summary",
]);

export type ArtifactBucket = "code" | "tests" | "documentation" | "other";

export function bucketArtifactKey(key: string): ArtifactBucket {
  if (CODE_ARTIFACT_KEYS.has(key)) {
    return "code";
  }
  if (TEST_ARTIFACT_KEYS.has(key)) {
    return "tests";
  }
  if (DOC_ARTIFACT_KEYS.has(key)) {
    return "documentation";
  }
  return "other";
}

export function groupArtifactsByBucket(
  artifacts: Record<string, JsonValue>,
): Record<ArtifactBucket, Record<string, JsonValue>> {
  const grouped: Record<ArtifactBucket, Record<string, JsonValue>> = {
    code: {},
    tests: {},
    documentation: {},
    other: {},
  };

  for (const [key, value] of Object.entries(artifacts)) {
    grouped[bucketArtifactKey(key)][key] = value;
  }

  return grouped;
}
