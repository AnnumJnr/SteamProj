/**
 * app/(auth)/layout.tsx
 * Auth route group layout.
 * Overrides the root layout's Navbar/Footer for a clean centered auth experience.
 * The (auth) folder name with parentheses is a Next.js route group —
 * it does NOT appear in the URL. /login and /register are the resulting paths.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { ROUTES } from "@/constants/routes";

export const metadata: Metadata = {
  title: {
    default: "STEMPath",
    template: "%s | STEMPath",
  },
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh flex flex-col bg-surface-base">
      {/* Minimal header — logo only */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-surface-border">
        <Link href={ROUTES.HOME} className="inline-flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <span className="font-display text-xl font-bold text-text-primary">
            STEM<span className="text-primary">Path</span>
          </span>
        </Link>
      </header>

      {/* Centered content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        {children}
      </div>
    </div>
  );
}
