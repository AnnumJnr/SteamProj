/**
 * components/layout/Navbar.tsx
 * Main navigation bar. Shows logo, nav links, search trigger, and auth state.
 * Reads auth state from useAuth() hook. No business logic.
 * All profile access uses optional chaining — profile can be null for
 * accounts created before the Phase 4 post_save signal was active.
 */



"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "./PageContainer";
import { ROUTES } from "@/constants/routes";
import { cn } from "@/lib/utils";
import * as authService from "@/services/authService";

const NAV_LINKS = [
  { label: "Explore Courses", href: ROUTES.COURSES },
  { label: "Combo Paths", href: ROUTES.COMBOS },
];

export function Navbar() {
  const { user, isAuthenticated, clearAuth } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  async function handleLogout() {
    try {
      const stored = localStorage.getItem("stempath-auth");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed?.state?.refreshToken) {
          await authService.logout(parsed.state.refreshToken);
        }
      }
    } catch {
      // Proceed with local logout regardless of server response
    } finally {
      clearAuth();
      router.push(ROUTES.HOME);
    }
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b border-surface-border bg-surface-base/90 backdrop-blur-sm">
      <PageContainer>
        <nav className="flex items-center justify-between h-16 gap-4">

          {/* Logo */}
          <Link href={ROUTES.HOME} className="flex items-center gap-2.5 flex-shrink-0">
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

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150",
                  pathname === link.href
                    ? "text-primary bg-primary-subtle"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">

            {/* Search */}
            <Link
              href={ROUTES.SEARCH}
              className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors duration-150"
              aria-label="Search"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </Link>

            {isAuthenticated && user ? (
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 p-1 rounded-full hover:bg-surface-raised transition-colors duration-150"
                  aria-label="User menu"
                >
                  <Avatar
                    src={user.profile?.avatar_url}
                    name={user.profile?.display_name}
                    email={user.email}
                    size="sm"
                  />
                </button>

                {isUserMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setIsUserMenuOpen(false)} />
                    <div className="absolute right-0 mt-2 w-52 bg-surface-overlay border border-surface-border rounded-xl shadow-lg z-20 animate-fade-in">
                      <div className="px-4 py-3 border-b border-surface-border">
                        <p className="text-sm font-medium text-text-primary truncate">
                          {user.profile?.display_name || "Your Account"}
                        </p>
                        <p className="text-xs text-text-muted truncate">{user.email}</p>
                      </div>
                      <div className="py-1">
                        <Link href={ROUTES.DASHBOARD} onClick={() => setIsUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors">
                          Dashboard
                        </Link>
                        <Link href={ROUTES.DASHBOARD_PROGRESS} onClick={() => setIsUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors">
                          My Progress
                        </Link>
                        <Link href={ROUTES.DASHBOARD_SAVED} onClick={() => setIsUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors">
                          Saved Items
                        </Link>
                        <div className="border-t border-surface-border my-1" />
                        <button
                          onClick={() => { setIsUserMenuOpen(false); handleLogout(); }}
                          className="w-full flex items-center gap-2 px-4 py-2 text-sm text-danger hover:bg-surface-raised transition-colors text-left"
                        >
                          Log out
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href={ROUTES.LOGIN}>
                  <Button variant="ghost" size="sm">Log in</Button>
                </Link>
                <Link href={ROUTES.REGISTER}>
                  <Button variant="primary" size="sm">Sign up</Button>
                </Link>
              </div>
            )}

            {/* Mobile menu toggle */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="md:hidden p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors"
              aria-label="Toggle menu"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isMenuOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                }
              </svg>
            </button>
          </div>
        </nav>

        {/* Mobile nav */}
        {isMenuOpen && (
          <div className="md:hidden py-3 border-t border-surface-border animate-fade-in">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsMenuOpen(false)}
                className={cn(
                  "flex items-center px-3 py-2.5 rounded-lg text-sm font-medium mb-1 transition-colors",
                  pathname === link.href
                    ? "text-primary bg-primary-subtle"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>
        )}
      </PageContainer>
    </header>
  );
}