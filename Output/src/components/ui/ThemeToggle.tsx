/**
 * components/ui/ThemeToggle.tsx
 * Switches the colour theme between light and dark.
 *
 * The icon shows what a click will switch TO, which is the convention users
 * expect from a two-state toggle: a sun means "go light".
 */

"use client";

import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { theme, setTheme, hasHydrated } = useTheme();

  // Hold the slot until the stored choice is known, so the icon does not
  // visibly swap after the first paint.
  if (!hasHydrated) {
    return <div className="w-9 h-9" aria-hidden="true" />;
  }

  const isDark = theme === "dark";
  const next = isDark ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors duration-150"
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      {isDark ? (
        // Sun — click to go light
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        // Moon — click to go dark
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  );
}
