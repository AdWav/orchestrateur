import en from "./locales/en.json";
import fr from "./locales/fr.json";
import type { Language, LocaleMessages, TranslationParams } from "./types";

export const LANGUAGE_STORAGE_KEY = "orchestrateur:language";

export const locales: Record<Language, LocaleMessages> = { fr, en };

export function isLanguage(value: string | null): value is Language {
  return value === "fr" || value === "en";
}

export function detectBrowserLanguage(): Language {
  if (typeof navigator === "undefined") {
    return "fr";
  }

  return navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
}

export function getInitialLanguage(): Language {
  if (typeof window === "undefined") {
    return "fr";
  }

  const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return isLanguage(storedLanguage) ? storedLanguage : detectBrowserLanguage();
}

export function getNestedValue(
  messages: LocaleMessages,
  path: string,
): string | undefined {
  const segments = path.split(".");
  let current: unknown = messages;

  for (const segment of segments) {
    if (current === null || typeof current !== "object") {
      return undefined;
    }
    current = (current as Record<string, unknown>)[segment];
  }

  return typeof current === "string" ? current : undefined;
}

export function interpolate(
  template: string,
  params?: TranslationParams,
): string {
  if (!params) {
    return template;
  }

  return template.replace(/\{\{(\w+)\}\}/g, (_, key: string) => {
    const value = params[key];
    return value === undefined ? `{{${key}}}` : String(value);
  });
}

export function createTranslator(language: Language) {
  const messages = locales[language];

  function t(path: string, params?: TranslationParams): string {
    const value = getNestedValue(messages, path);
    if (value === undefined) {
      return path;
    }
    return interpolate(value, params);
  }

  function mapLabel<T extends Record<string, string>>(
    table: T,
    key: string,
    fallback?: string,
  ): string {
    return table[key as keyof T] ?? fallback ?? key;
  }

  return {
    language,
    messages,
    t,
    runtimeRoleLabel: (role: string) =>
      mapLabel(messages.runtime.roleLabels, role, role),
    meshServiceLabel: (key: string) =>
      mapLabel(messages.mesh.serviceLabels, key, key),
    approvalState: (approved: boolean | null) => {
      if (approved === true) {
        return messages.status.approved;
      }
      if (approved === false) {
        return messages.status.blocked;
      }
      return messages.status.inFlow;
    },
    passState: (passed: boolean) =>
      passed ? messages.status.passed : messages.status.blocked,
    analysisAxis: (axis: string) =>
      mapLabel(messages.repoAudit.axisLabels, axis, axis),
    healthStatus: (status: string) =>
      mapLabel(messages.apiHealth.statusLabels, status, status),
    artifactKey: (key: string) =>
      mapLabel(messages.artifactKeys, key, key.replace(/_/g, " ")),
    teamName: (teamId: string, fallback: string) =>
      messages.catalog.teams[teamId as keyof typeof messages.catalog.teams]
        ?.name ?? fallback,
    teamPurpose: (teamId: string, fallback: string) =>
      messages.catalog.teams[teamId as keyof typeof messages.catalog.teams]
        ?.purpose ?? fallback,
    teamGuardrails: (teamId: string, fallback: string[]) => {
      const localized =
        messages.catalog.teams[teamId as keyof typeof messages.catalog.teams]
          ?.guardrails;
      return localized ?? fallback;
    },
    teamHandoffs: (teamId: string, fallback: string[]) => {
      const localized =
        messages.catalog.teams[teamId as keyof typeof messages.catalog.teams]
          ?.handoffs;
      return localized ?? fallback;
    },
    teamMethodology: (methodology: string | null | undefined) => {
      if (!methodology) {
        return methodology ?? "";
      }
      return (
        messages.catalog.methodologies[
          methodology as keyof typeof messages.catalog.methodologies
        ] ?? methodology
      );
    },
    agentMission: (agentId: string, fallback: string) => {
      const entry =
        messages.catalog.agents[agentId as keyof typeof messages.catalog.agents];
      return entry?.mission ?? fallback;
    },
    roleResponsibility: (role: string, fallback: string) => {
      const agentEntry =
        messages.catalog.agents[role as keyof typeof messages.catalog.agents];
      if (agentEntry?.mission) {
        return agentEntry.mission;
      }
      return fallback;
    },
  };
}

export type Translator = ReturnType<typeof createTranslator>;

let activeTranslator = createTranslator("fr");

export function syncActiveTranslator(language: Language): Translator {
  activeTranslator = createTranslator(language);
  return activeTranslator;
}

export function getActiveTranslator(): Translator {
  return activeTranslator;
}

export function applyDocumentLanguage(language: Language) {
  const messages = locales[language];

  if (typeof window !== "undefined") {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }

  if (typeof document !== "undefined") {
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
    document.title = messages.app.title;

    const meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.setAttribute("content", messages.app.description);
    }
  }
}
