import type { LiveNumericKey } from "./samplingFieldSpecs";

export type SamplingGroupMode = "flat" | "role" | "impact";

export type SamplingTextFieldKey = "stop" | "logit_bias";

export type SamplingFieldGroup = {
  id: string;
  numeric: LiveNumericKey[];
  text?: SamplingTextFieldKey[];
};

/** Regroupement par rôle (docs/EXPLAIN.md §3). */
export const ROLE_FIELD_GROUPS: SamplingFieldGroup[] = [
  {
    id: "length",
    numeric: ["num_predict"],
    text: ["stop"],
  },
  {
    id: "creativity",
    numeric: ["temperature", "mirostat", "mirostat_eta", "mirostat_tau"],
  },
  {
    id: "pool",
    numeric: ["top_p", "top_k", "min_p"],
  },
  {
    id: "antiRepeat",
    numeric: [
      "repeat_penalty",
      "repeat_last_n",
      "presence_penalty",
      "frequency_penalty",
    ],
  },
  {
    id: "surgery",
    text: ["logit_bias"],
    numeric: [],
  },
];

/** Regroupement par impact (docs/EXPLAIN.md §4). */
export const IMPACT_FIELD_GROUPS: SamplingFieldGroup[] = [
  {
    id: "veryStrong",
    numeric: ["temperature", "top_p", "repeat_penalty", "num_predict"],
  },
  {
    id: "strong",
    numeric: ["mirostat", "mirostat_eta", "mirostat_tau", "top_k", "min_p"],
  },
  {
    id: "medium",
    numeric: ["presence_penalty", "frequency_penalty", "repeat_last_n"],
  },
  {
    id: "targeted",
    numeric: [],
    text: ["logit_bias", "stop"],
  },
];

export function groupsForMode(mode: SamplingGroupMode): SamplingFieldGroup[] {
  if (mode === "role") {
    return ROLE_FIELD_GROUPS;
  }
  if (mode === "impact") {
    return IMPACT_FIELD_GROUPS;
  }
  return [];
}
