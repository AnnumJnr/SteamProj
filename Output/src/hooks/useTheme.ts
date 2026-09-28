/**
 * hooks/useTheme.ts
 * Responsibility: read and write the active colour theme ONLY.
 *
 * Two states: "light" and "dark". The choice is persisted to localStorage and
 * applied as data-theme on <html>, which is what the light palette in
 * styles/globals.css keys off.
 *
 * With nothing stored yet, the OS preference decides the starting theme. That
 * is a first-run default only — once the user toggles, the stored choice wins
 * and the OS setting is no longer consulted.
 *
 * First paint is handled by the inline script in app/layout.tsx, not here —
 * a React effect runs after paint, which would flash the wrong palette.
 * This hook owns the theme after that point.
 */

"use client";

import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

// Must match the key read by the inline script in app/layout.tsx.
export const THEME_STORAGE_KEY = "stempath-theme";

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("dark");
  // False until the stored choice has been read. The toggle must wait for this
  // or it renders the wrong icon for a frame, the same way the auth store did.
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(THEME_STORAGE_KEY);
    } catch {
      // Private browsing or blocked storage — fall through to the OS default.
    }

    if (stored === "light" || stored === "dark") {
      setThemeState(stored);
    } else {
      // No stored choice: match the OS for this first visit. The inline script
      // already painted this same value, so nothing changes visually here.
      setThemeState(
        window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"
      );
    }
    setHasHydrated(true);
  }, []);

  const setTheme = useCallback((next: Theme) => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Storage unavailable — the theme still applies for this session.
    }
    setThemeState(next);
    applyTheme(next);
  }, []);

  return { theme, setTheme, hasHydrated };
}
