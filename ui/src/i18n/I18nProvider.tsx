import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import {
  applyLanguage,
  getI18nCopy,
  getInitialLanguage,
  type I18nCopy,
  type Language,
} from "./translations";

type I18nContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  copy: I18nCopy;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: PropsWithChildren) {
  const [language, setLanguageState] = useState<Language>(() => {
    const initialLanguage = getInitialLanguage();
    applyLanguage(initialLanguage);
    return initialLanguage;
  });

  const setLanguage = useCallback((nextLanguage: Language) => {
    applyLanguage(nextLanguage);
    setLanguageState(nextLanguage);
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      copy: getI18nCopy(language),
    }),
    [language, setLanguage],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);

  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider.");
  }

  return context;
}
