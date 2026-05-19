import type en from "./locales/en.json";

export type Language = "fr" | "en";

export type LocaleMessages = typeof en;

export type TranslationParams = Record<string, string | number>;
