/**
 * components/shared/HomeCTA.tsx
 * Closing call-to-action on the homepage.
 *
 * Client component because the homepage is a server component and auth state
 * lives in localStorage, which the server cannot read. Signed-in visitors get
 * a route into their dashboard instead of a prompt to create a second account.
 */

"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { ROUTES } from "@/constants/routes";

export function HomeCTA() {
  const { isAuthenticated, hasHydrated } = useAuth();

  // Hold the block's height steady until localStorage is read, so the copy
  // does not visibly swap after the first paint.
  if (!hasHydrated) {
    return <div className="h-[13.5rem]" aria-hidden="true" />;
  }

  if (isAuthenticated) {
    return (
      <>
        <h2 className="text-2xl font-bold text-text-primary mb-3">
          Pick up where you left off
        </h2>
        <p className="text-text-secondary mb-6 leading-relaxed">
          Your progress, saved courses, and Combo paths are waiting in your dashboard.
        </p>
        <div className="flex items-center gap-3 justify-center flex-wrap">
          <Link href={ROUTES.DASHBOARD}>
            <Button size="lg">Go to dashboard</Button>
          </Link>
          <Link href={ROUTES.COMBOS}>
            <Button size="lg" variant="ghost">Browse Combo paths</Button>
          </Link>
        </div>
      </>
    );
  }

  return (
    <>
      <h2 className="text-2xl font-bold text-text-primary mb-3">
        Ready to start learning?
      </h2>
      <p className="text-text-secondary mb-6 leading-relaxed">
        Create a free account and track your progress across every course and Combo path.
      </p>
      <div className="flex items-center gap-3 justify-center flex-wrap">
        <Link href={ROUTES.REGISTER}>
          <Button size="lg">Get started free</Button>
        </Link>
        <Link href={ROUTES.COURSES}>
          <Button size="lg" variant="ghost">Explore without signing up</Button>
        </Link>
      </div>
    </>
  );
}
