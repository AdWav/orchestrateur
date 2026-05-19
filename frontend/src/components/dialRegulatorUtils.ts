export type DialRegulatorVariant = "digital" | "rotary";
export type DialRegulatorSize = "sm" | "md" | "lg";

export const DIAL_SIZE_PX: Record<DialRegulatorSize, number> = {
  sm: 72,
  md: 120,
  lg: 200,
};

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function ratio(value: number, min: number, max: number): number {
  if (max <= min) return 0;
  return clamp((value - min) / (max - min), 0, 1);
}

/**
 * Couleur du compte-tour : peu (bas) → beaucoup (haut).
 * Bleu = faible / stop, rouge = fort.
 */
export function digitalGaugeColor(t: number): string {
  const level = clamp(t, 0, 1);
  if (level >= 0.85) return "#ff3d4a";
  if (level >= 0.65) return "#ff5544";
  if (level >= 0.45) return "#e85dff";
  if (level >= 0.25) return "#4a9eff";
  return "#2d7dd2";
}

export function rotaryAmberColor(t: number): string {
  const warm = "#ffb347";
  const hot = "#ff8c1a";
  return t > 0.5 ? hot : warm;
}

export function angleToValue(
  angleDeg: number,
  min: number,
  max: number,
  startAngleDeg = 90,
): number {
  const span = 360;
  const offset = ((angleDeg - startAngleDeg + 360) % 360) / span;
  return Math.round(min + offset * (max - min));
}

export function valueToLitCount(
  value: number,
  min: number,
  max: number,
  segmentCount: number,
): number {
  const t = ratio(value, min, max);
  return Math.round(t * segmentCount);
}

export function formatDialValue(value: number, max: number): string {
  const digits = String(Math.round(max)).length;
  return String(Math.round(value)).padStart(digits, "0");
}
