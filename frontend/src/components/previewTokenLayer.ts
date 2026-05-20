/** Palette cyclique pour le calque de tokenisation (une teinte par fragment streamé). */
export const PREVIEW_TOKEN_TONE_COUNT = 12;

export function previewTokenTone(index: number): number {
  return index % PREVIEW_TOKEN_TONE_COUNT;
}
