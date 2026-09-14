/**
 * app/(auth)/login/page.tsx
 * Login page. Supports email/password and Google OAuth.
 *
 * Flow:
 *   1. User submits form → authService.login() → setAuth() → redirect to dashboard
 *   2. User clicks Google → Google One Tap → authService.googleAuth() → setAuth() → redirect
 *
 * Analytics: USER_LOGGED_IN is fired by the BACKEND on successful auth.
 * This page fires nothing — no duplicate events.
 */

/**
 *
 * Backend auth response shape: { user: {...}, access: "...", refresh: "..." }
 * Tokens are at the top level — setAuth receives them extracted into a TokenPair.
 */

"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useGoogleSignIn } from "@/hooks/useGoogleSignIn";
import * as authService from "@/services/authService";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ROUTES } from "@/constants/routes";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGoogleCredential(idToken: string) {
    setError(null);
    setIsLoading(true);

    try {
      const response = await authService.googleAuth(idToken);

      setAuth(response.user, {
        access: response.access,
        refresh: response.refresh,
      });

      router.push(ROUTES.DASHBOARD);
    } catch (err: unknown) {
      const message =
        (err as { detail?: string })?.detail ||
        (err as { message?: string })?.message ||
        "Google sign-in failed. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  const googleButtonRef = useGoogleSignIn(handleGoogleCredential);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await authService.login({ email, password });

      // Tokens are at the top level of the response, not nested under "tokens"
      // Backend shape: { user: {...}, access: "...", refresh: "..." }
      setAuth(response.user, {
        access: response.access,
        refresh: response.refresh,
      });

      router.push(ROUTES.DASHBOARD);
    } catch (err: unknown) {
      const message =
        (err as { detail?: string })?.detail ||
        (err as { message?: string })?.message ||
        "Invalid email or password. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md animate-fade-in-up">
      <div className="bg-surface-raised border border-surface-border rounded-2xl p-8 shadow-lg">

        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-text-primary mb-1">Welcome back</h1>
          <p className="text-sm text-text-secondary">
            Log in to continue your learning journey
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mb-5 px-4 py-3 rounded-lg bg-danger/10 border border-danger/30 text-sm text-danger">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email address"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
          />

          <Input
            label="Password"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />

          <Button type="submit" fullWidth isLoading={isLoading} className="mt-2">
            Log in
          </Button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-surface-border" />
          </div>
          <div className="relative flex justify-center">
            <span className="px-3 bg-surface-raised text-xs text-text-muted">or</span>
          </div>
        </div>

        {/* Google button — rendered by Google Identity Services into this container */}
        <div
          ref={googleButtonRef}
          className="flex justify-center [&>div]:!w-full"
          aria-disabled={isLoading}
        />
        {!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID && (
          <p className="mt-2 text-center text-xs text-text-muted">
            Google sign-in is not configured (NEXT_PUBLIC_GOOGLE_CLIENT_ID missing).
          </p>
        )}

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-text-muted">
          Don&apos;t have an account?{" "}
          <Link
            href={ROUTES.REGISTER}
            className="text-primary hover:text-primary-hover font-medium transition-colors"
          >
            Sign up for free
          </Link>
        </p>
      </div>
    </div>
  );
}