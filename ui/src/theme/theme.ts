export type ThemeMode = "light" | "dark";
export type ResolvedTheme = ThemeMode;

const THEME_STORAGE_KEY = "orchestrateur:theme-mode";
const DARK_THEME_CLASS = "ion-palette-dark";
const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";

function isThemeMode(value: string | null): value is ThemeMode {
  return value === "light" || value === "dark";
}

export function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "light";
  }

  return window.matchMedia(SYSTEM_DARK_QUERY).matches ? "dark" : "light";
}

export function getInitialThemeMode(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  const storedThemeMode = window.localStorage.getItem(THEME_STORAGE_KEY);
  return isThemeMode(storedThemeMode) ? storedThemeMode : getSystemTheme();
}

export function persistThemeMode(themeMode: ThemeMode) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(THEME_STORAGE_KEY, themeMode);
}

export function applyResolvedTheme(theme: ResolvedTheme) {
  if (typeof document === "undefined") {
    return;
  }

  const root = document.documentElement;
  root.classList.toggle(DARK_THEME_CLASS, theme === "dark");
  root.dataset.theme = theme;
}
