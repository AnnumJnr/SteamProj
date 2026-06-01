/**
 * components/layout/Footer.tsx
 * Site footer. Static content — no data fetching, no auth state.
 */

import Link from "next/link";
import { PageContainer } from "./PageContainer";
import { ROUTES } from "@/constants/routes";

export function Footer() {
  return (
    <footer className="border-t border-surface-border bg-surface-base mt-auto">
      <PageContainer>
        <div className="py-12 grid grid-cols-1 md:grid-cols-4 gap-8">

          {/* Brand */}
          <div className="md:col-span-1">
            <Link href={ROUTES.HOME} className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <span className="font-display text-lg font-bold text-text-primary">
                STEM<span className="text-primary">Path</span>
              </span>
            </Link>
            <p className="text-sm text-text-muted leading-relaxed">
              Curated STEM learning paths for every age and level.
            </p>
          </div>

          {/* Learn */}
          <div>
            <h4 className="text-sm font-semibold text-text-primary mb-3">Learn</h4>
            <ul className="space-y-2">
              <li><Link href={ROUTES.COURSES} className="text-sm text-text-muted hover:text-primary transition-colors">Explore Courses</Link></li>
              <li><Link href={ROUTES.COMBOS} className="text-sm text-text-muted hover:text-primary transition-colors">Combo Paths</Link></li>
              <li><Link href={ROUTES.SEARCH} className="text-sm text-text-muted hover:text-primary transition-colors">Search</Link></li>
            </ul>
          </div>

          {/* Account */}
          <div>
            <h4 className="text-sm font-semibold text-text-primary mb-3">Account</h4>
            <ul className="space-y-2">
              <li><Link href={ROUTES.LOGIN} className="text-sm text-text-muted hover:text-primary transition-colors">Log in</Link></li>
              <li><Link href={ROUTES.REGISTER} className="text-sm text-text-muted hover:text-primary transition-colors">Sign up</Link></li>
              <li><Link href={ROUTES.DASHBOARD} className="text-sm text-text-muted hover:text-primary transition-colors">Dashboard</Link></li>
            </ul>
          </div>

          {/* STEM Categories */}
          <div>
            <h4 className="text-sm font-semibold text-text-primary mb-3">Categories</h4>
            <ul className="space-y-2">
              {["Computer Science", "Mathematics", "Natural Sciences", "Engineering"].map((cat) => (
                <li key={cat}>
                  <Link
                    href={`${ROUTES.COURSES}?category=${encodeURIComponent(cat)}`}
                    className="text-sm text-text-muted hover:text-primary transition-colors"
                  >
                    {cat}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="py-4 border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-text-muted">
            © {new Date().getFullYear()} STEMPath. All rights reserved.
          </p>
          <p className="text-xs text-text-muted">
            Built for curious minds everywhere.
          </p>
        </div>
      </PageContainer>
    </footer>
  );
}
