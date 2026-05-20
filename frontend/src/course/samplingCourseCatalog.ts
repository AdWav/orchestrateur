import type { LiveNumericKey } from "../components/samplingFieldSpecs";

/** Etape du pipeline de decodage (docs/EXPLAIN.md). */
export type PipelineStepId =
  | "logits"
  | "logit_bias"
  | "anti_repeat"
  | "temperature_mirostat"
  | "filters"
  | "sample"
  | "constraints";

export type CourseFieldKey = LiveNumericKey | "stop" | "logit_bias";

export type SamplingCourseEntry = {
  fieldKey: CourseFieldKey;
  /** Cle API Ollama (identique au fieldKey sauf stop / logit_bias). */
  apiKey: string;
  pipelineStepId: PipelineStepId;
  /** Ordre d'affichage dans la chaine (1 = premier). */
  pipelineOrder: number;
  symbols: string[];
  /** Cle i18n : course.equations.<equationKey> */
  equationKey: string;
  roleGroupId?: string;
  impactGroupId?: string;
  relatedFields?: CourseFieldKey[];
  /** Cles i18n : course.references.<key> */
  referenceKeys: string[];
};

export const PIPELINE_STEPS: {
  id: PipelineStepId;
  order: number;
  fieldKeys: CourseFieldKey[];
}[] = [
  { id: "logits", order: 1, fieldKeys: [] },
  { id: "logit_bias", order: 2, fieldKeys: ["logit_bias"] },
  {
    id: "anti_repeat",
    order: 3,
    fieldKeys: [
      "repeat_penalty",
      "repeat_last_n",
      "presence_penalty",
      "frequency_penalty",
    ],
  },
  {
    id: "temperature_mirostat",
    order: 4,
    fieldKeys: ["temperature", "mirostat", "mirostat_eta", "mirostat_tau"],
  },
  { id: "filters", order: 5, fieldKeys: ["top_k", "top_p", "min_p"] },
  { id: "sample", order: 6, fieldKeys: [] },
  { id: "constraints", order: 7, fieldKeys: ["num_predict", "stop"] },
];

export const SAMPLING_COURSE_ENTRIES: SamplingCourseEntry[] = [
  {
    fieldKey: "logit_bias",
    apiKey: "logit_bias",
    pipelineStepId: "logit_bias",
    pipelineOrder: 2,
    symbols: ["z_i", "bias_i", "z'_i"],
    equationKey: "logit_bias",
    roleGroupId: "surgery",
    impactGroupId: "targeted",
    referenceKeys: ["explain"],
  },
  {
    fieldKey: "repeat_penalty",
    apiKey: "repeat_penalty",
    pipelineStepId: "anti_repeat",
    pipelineOrder: 3,
    symbols: ["z_i", "history"],
    equationKey: "repeat_penalty",
    roleGroupId: "antiRepeat",
    impactGroupId: "veryStrong",
    relatedFields: ["repeat_last_n"],
    referenceKeys: ["explain", "mirostat"],
  },
  {
    fieldKey: "repeat_last_n",
    apiKey: "repeat_last_n",
    pipelineStepId: "anti_repeat",
    pipelineOrder: 3,
    symbols: ["N"],
    equationKey: "repeat_last_n",
    roleGroupId: "antiRepeat",
    impactGroupId: "medium",
    relatedFields: ["repeat_penalty"],
    referenceKeys: ["explain"],
  },
  {
    fieldKey: "presence_penalty",
    apiKey: "presence_penalty",
    pipelineStepId: "anti_repeat",
    pipelineOrder: 3,
    symbols: ["alpha_pres"],
    equationKey: "presence_penalty",
    roleGroupId: "antiRepeat",
    impactGroupId: "medium",
    referenceKeys: ["explain"],
  },
  {
    fieldKey: "frequency_penalty",
    apiKey: "frequency_penalty",
    pipelineStepId: "anti_repeat",
    pipelineOrder: 3,
    symbols: ["alpha_freq"],
    equationKey: "frequency_penalty",
    roleGroupId: "antiRepeat",
    impactGroupId: "medium",
    referenceKeys: ["explain"],
  },
  {
    fieldKey: "temperature",
    apiKey: "temperature",
    pipelineStepId: "temperature_mirostat",
    pipelineOrder: 4,
    symbols: ["T", "z_i", "P(i)"],
    equationKey: "temperature",
    roleGroupId: "creativity",
    impactGroupId: "veryStrong",
    relatedFields: ["mirostat", "mirostat_eta", "mirostat_tau"],
    referenceKeys: ["mirostat", "holtzman", "explain"],
  },
  {
    fieldKey: "mirostat",
    apiKey: "mirostat",
    pipelineStepId: "temperature_mirostat",
    pipelineOrder: 4,
    symbols: ["k", "tau", "mu", "eta"],
    equationKey: "mirostat",
    roleGroupId: "creativity",
    impactGroupId: "strong",
    relatedFields: ["mirostat_eta", "mirostat_tau", "temperature"],
    referenceKeys: ["mirostat"],
  },
  {
    fieldKey: "mirostat_eta",
    apiKey: "mirostat_eta",
    pipelineStepId: "temperature_mirostat",
    pipelineOrder: 4,
    symbols: ["eta", "mu", "e"],
    equationKey: "mirostat_eta",
    roleGroupId: "creativity",
    impactGroupId: "strong",
    relatedFields: ["mirostat", "mirostat_tau"],
    referenceKeys: ["mirostat"],
  },
  {
    fieldKey: "mirostat_tau",
    apiKey: "mirostat_tau",
    pipelineStepId: "temperature_mirostat",
    pipelineOrder: 4,
    symbols: ["tau", "S(X)"],
    equationKey: "mirostat_tau",
    roleGroupId: "creativity",
    impactGroupId: "strong",
    relatedFields: ["mirostat", "mirostat_eta"],
    referenceKeys: ["mirostat"],
  },
  {
    fieldKey: "top_k",
    apiKey: "top_k",
    pipelineStepId: "filters",
    pipelineOrder: 5,
    symbols: ["k", "V^(k)"],
    equationKey: "top_k",
    roleGroupId: "pool",
    impactGroupId: "strong",
    relatedFields: ["top_p", "min_p"],
    referenceKeys: ["mirostat", "holtzman", "explain"],
  },
  {
    fieldKey: "top_p",
    apiKey: "top_p",
    pipelineStepId: "filters",
    pipelineOrder: 5,
    symbols: ["p", "V^(p)"],
    equationKey: "top_p",
    roleGroupId: "pool",
    impactGroupId: "veryStrong",
    relatedFields: ["top_k", "min_p"],
    referenceKeys: ["holtzman", "explain"],
  },
  {
    fieldKey: "min_p",
    apiKey: "min_p",
    pipelineStepId: "filters",
    pipelineOrder: 5,
    symbols: ["p_min", "P(i)"],
    equationKey: "min_p",
    roleGroupId: "pool",
    impactGroupId: "strong",
    relatedFields: ["top_p", "top_k"],
    referenceKeys: ["explain"],
  },
  {
    fieldKey: "num_predict",
    apiKey: "num_predict",
    pipelineStepId: "constraints",
    pipelineOrder: 7,
    symbols: ["t", "T_max"],
    equationKey: "num_predict",
    roleGroupId: "length",
    impactGroupId: "veryStrong",
    relatedFields: ["stop"],
    referenceKeys: ["explain"],
  },
  {
    fieldKey: "stop",
    apiKey: "stop",
    pipelineStepId: "constraints",
    pipelineOrder: 7,
    symbols: ["s"],
    equationKey: "stop",
    roleGroupId: "length",
    impactGroupId: "targeted",
    relatedFields: ["num_predict"],
    referenceKeys: ["explain"],
  },
];

export const COURSE_FIELD_ORDER: CourseFieldKey[] = SAMPLING_COURSE_ENTRIES.map(
  (e) => e.fieldKey,
);

export function courseEntryForField(
  fieldKey: CourseFieldKey,
): SamplingCourseEntry | undefined {
  return SAMPLING_COURSE_ENTRIES.find((e) => e.fieldKey === fieldKey);
}
