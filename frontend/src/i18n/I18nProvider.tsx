import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import {
  applyDocumentLanguage,
  createTranslator,
  getInitialLanguage,
  syncActiveTranslator,
  type Translator,
} from "./core";
import type { Language } from "./types";

type I18nContextValue = Translator & {
  language: Language;
  setLanguage: (language: Language) => void;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: PropsWithChildren) {
  const [language, setLanguageState] = useState<Language>(() => {
    const initialLanguage = getInitialLanguage();
    syncActiveTranslator(initialLanguage);
    applyDocumentLanguage(initialLanguage);
    return initialLanguage;
  });

  const setLanguage = useCallback((nextLanguage: Language) => {
    syncActiveTranslator(nextLanguage);
    applyDocumentLanguage(nextLanguage);
    setLanguageState(nextLanguage);
  }, []);

  const value = useMemo<I18nContextValue>(() => {
    const translator = createTranslator(language);
    return {
      ...translator,
      language,
      setLanguage,
    };
  }, [language, setLanguage]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);

  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider.");
  }

  return context;
}
