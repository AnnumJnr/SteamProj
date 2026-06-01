/**
 * app/(auth)/register/page.tsx
 * Registration page. Email/password only for MVP.
 *
 * Flow:
 *   User submits → authService.register() → setAuth() → redirect to dashboard
 *
 * Field names match backend RegisterSerializer exactly:
 *   email, password1, password2
 * Source: apps/users/serializers.py → RegisterSerializer
 *
 * Analytics: USER_SIGNED_UP is fired by the BACKEND on successful registration.
 * This page fires nothing — no duplicate events.
 */

/**
 * Backend RegisterSerializer expects: email, password1, password2
 * Backend response shape: { user: {...}, access: "...", refresh: "..." }
 * Source: apps/users/serializers.py → RegisterSerializer
 *         apps/users/views.py → RegisterView
 */

"use client";
 
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import * as authService from "@/services/authService";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ROUTES } from "@/constants/routes";
 
export default function RegisterPage() {
  const router = useRouter();
  const { setAuth } = useAuth();
 
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);
 
  function validateForm(): boolean {
    const newErrors: Record<string, string> = {};
    if (!email) newErrors.email = "Email is required.";
    if (!password) newErrors.password = "Password is required.";
    if (password.length > 0 && password.length < 8)
      newErrors.password = "Password must be at least 8 characters.";
    if (password !== passwordConfirm)
      newErrors.password_confirm = "Passwords do not match.";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }
 
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setGlobalError(null);
    setErrors({});
 
    if (!validateForm()) return;
 
    setIsLoading(true);
    try {
      const response = await authService.register({
        email,
        password,
        password_confirm: passwordConfirm,
      });
 
      // Tokens are at the top level: { user, access, refresh }
      setAuth(response.user, {
        access: response.access,
        refresh: response.refresh,
      });
 
      router.push(ROUTES.DASHBOARD);
    } catch (err: unknown) {
      const apiErr = err as {
        detail?: string;
        message?: string;
        errors?: Record<string, string[]>;
      };
      if (apiErr?.errors) {
        const flat: Record<string, string> = {};
        Object.entries(apiErr.errors).forEach(([key, msgs]) => {
          flat[key] = msgs[0];
        });
        setErrors(flat);
      } else {
        setGlobalError(
          apiErr?.detail ||
            apiErr?.message ||
            "Registration failed. Please try again."
        );
      }
    } finally {
      setIsLoading(false);
    }
  }
 
  return (
    <div className="w-full max-w-md animate-fade-in-up">
      <div className="bg-surface-raised border border-surface-border rounded-2xl p-8 shadow-lg">
 
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-text-primary mb-1">
            Create your account
          </h1>
          <p className="text-sm text-text-secondary">
            Start learning STEM for free today
          </p>
        </div>
 
        {/* Global error */}
        {globalError && (
          <div className="mb-5 px-4 py-3 rounded-lg bg-danger/10 border border-danger/30 text-sm text-danger">
            {globalError}
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
            error={errors.email}
            required
            autoComplete="email"
            autoFocus
          />
 
          {/* Password with show/hide toggle */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-primary">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full px-3 py-2 pr-10 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-danger" role="alert">{errors.password}</p>
            )}
          </div>
 
          {/* Confirm password with show/hide toggle */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-primary">
              Confirm password
            </label>
            <div className="relative">
              <input
                type={showPasswordConfirm ? "text" : "password"}
                placeholder="Repeat your password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full px-3 py-2 pr-10 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                aria-label={showPasswordConfirm ? "Hide password" : "Show password"}
              >
                {showPasswordConfirm ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            {errors.password_confirm && (
              <p className="text-xs text-danger" role="alert">{errors.password_confirm}</p>
            )}
          </div>
 
          <Button type="submit" fullWidth isLoading={isLoading} className="mt-2">
            Create account
          </Button>
        </form>
 
        {/* Footer */}
        <p className="mt-6 text-center text-sm text-text-muted">
          Already have an account?{" "}
          <Link
            href={ROUTES.LOGIN}
            className="text-primary hover:text-primary-hover font-medium transition-colors"
          >
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
 