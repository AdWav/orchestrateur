import type { SamplingProfile } from "../lib/api";

/** Champs numeriques du profil live (int ou float), distincts des champs texte. */
export type LiveNumericKey = Exclude<keyof SamplingProfile, "logit_bias" | "stop">;

export type LiveNumericState = Pick<SamplingProfile, LiveNumericKey>;

export type LiveTextState = {
  stopText: string;
  logitBiasText: string;
};

export type LiveFormState = LiveNumericState & LiveTextState;

export type FieldSpec = {
  min: number;
  max: number;
  step: number;
  integer: boolean;
};

export const SAMPLING_FIELD_SPECS: Record<LiveNumericKey, FieldSpec> = {
  temperature: { min: 0, max: 2, step: 0.05, integer: false },
  top_k: { min: 0, max: 200, step: 1, integer: true },
  top_p: { min: 0, max: 1, step: 0.01, integer: false },
  min_p: { min: 0, max: 1, step: 0.01, integer: false },
  mirostat: { min: 0, max: 2, step: 1, integer: true },
  mirostat_eta: { min: 0.01, max: 10, step: 0.01, integer: false },
  mirostat_tau: { min: 0, max: 10, step: 0.1, integer: false },
  presence_penalty: { min: 0, max: 2, step: 0.05, integer: false },
  frequency_penalty: { min: 0, max: 2, step: 0.05, integer: false },
  repeat_penalty: { min: 0, max: 3, step: 0.05, integer: false },
  repeat_last_n: { min: 0, max: 256, step: 1, integer: true },
  num_predict: { min: 16, max: 4096, step: 16, integer: true },
};

export const LIVE_NUMERIC_FIELD_ORDER: LiveNumericKey[] = [
  "temperature",
  "top_k",
  "top_p",
  "min_p",
  "mirostat",
  "mirostat_eta",
  "mirostat_tau",
  "presence_penalty",
  "frequency_penalty",
  "repeat_penalty",
  "repeat_last_n",
  "num_predict",
];

const INTEGER_FIELDS = new Set<LiveNumericKey>(
  LIVE_NUMERIC_FIELD_ORDER.filter((key) => SAMPLING_FIELD_SPECS[key].integer),
);

export function snapToSpec(raw: number, spec: FieldSpec): number {
  const clamped = Math.min(spec.max, Math.max(spec.min, raw));
  if (spec.integer) {
    return Math.round(clamped);
  }
  const stepDecimals = countDecimals(spec.step);
  return Number(clamped.toFixed(stepDecimals));
}

export const DIAL_STEPS = 60;

export function samplingValueToDial(
  value: number,
  spec: FieldSpec,
  dialMax = DIAL_STEPS,
): number {
  const span = spec.max - spec.min;
  if (span <= 0) {
    return 0;
  }
  const t = (value - spec.min) / span;
  return Math.round(Math.min(dialMax, Math.max(0, t * dialMax)));
}

export function dialToSamplingValue(
  dial: number,
  spec: FieldSpec,
  dialMax = DIAL_STEPS,
): number {
  const span = spec.max - spec.min;
  const raw = spec.min + (dial / dialMax) * span;
  return snapToSpec(raw, spec);
}

export function formatNumericDisplay(value: number, spec: FieldSpec): string {
  if (spec.integer) {
    return String(Math.round(value));
  }
  const decimals = countDecimals(spec.step);
  return value.toFixed(decimals);
}

export function formToSamplingProfile(form: LiveFormState): SamplingProfile {
  const profile: SamplingProfile = {
    temperature: form.temperature,
    top_k: form.top_k,
    top_p: form.top_p,
    min_p: form.min_p,
    mirostat: form.mirostat,
    mirostat_eta: form.mirostat_eta,
    mirostat_tau: form.mirostat_tau,
    presence_penalty: form.presence_penalty,
    frequency_penalty: form.frequency_penalty,
    repeat_penalty: form.repeat_penalty,
    repeat_last_n: form.repeat_last_n,
    num_predict: form.num_predict,
    stop: parseStopLines(form.stopText),
    logit_bias: parseLogitBiasLines(form.logitBiasText),
  };
  for (const key of INTEGER_FIELDS) {
    const value = profile[key];
    if (value !== null && value !== undefined) {
      profile[key] = Math.round(value);
    }
  }
  return profile;
}

function countDecimals(step: number): number {
  const text = String(step);
  const dot = text.indexOf(".");
  return dot === -1 ? 0 : text.length - dot - 1;
}

function parseStopLines(raw: string): string[] | null {
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  return lines.length > 0 ? lines : null;
}

function parseLogitBiasLines(raw: string): Record<string, number> | null {
  const entries: Record<string, number> = {};
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const separator = trimmed.indexOf(":");
    if (separator <= 0) {
      continue;
    }
    const token = trimmed.slice(0, separator).trim();
    const weight = Number(trimmed.slice(separator + 1).trim());
    if (!token || !Number.isFinite(weight)) {
      continue;
    }
    entries[token] = weight;
  }
  return Object.keys(entries).length > 0 ? entries : null;
}

export function profileToLiveForm(profile: SamplingProfile): LiveFormState {
  return {
    temperature: profile.temperature,
    top_k: profile.top_k,
    top_p: profile.top_p,
    min_p: profile.min_p,
    mirostat: profile.mirostat,
    mirostat_eta: profile.mirostat_eta,
    mirostat_tau: profile.mirostat_tau,
    presence_penalty: profile.presence_penalty,
    frequency_penalty: profile.frequency_penalty,
    repeat_penalty: profile.repeat_penalty,
    repeat_last_n: profile.repeat_last_n,
    num_predict: profile.num_predict,
    stopText: (profile.stop ?? []).join("\n"),
    logitBiasText: formatLogitBias(profile.logit_bias),
  };
}

function formatLogitBias(bias: Record<string, number> | null | undefined): string {
  if (!bias) {
    return "";
  }
  return Object.entries(bias)
    .map(([token, weight]) => `${token}:${weight}`)
    .join("\n");
}
