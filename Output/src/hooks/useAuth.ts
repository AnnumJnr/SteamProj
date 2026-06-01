/**
 * hooks/useAuth.ts
 * Responsibility: read and write the auth store ONLY.
 * Forbidden: API calls, navigation, data transformation, analytics.
 *
 * Components must not import from stores/ directly.
 * They access auth state exclusively through this hook.
 */

"use client";

import { useAuthStore } from "@/stores/authStore";

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setAuth = useAuthStore((s) => s.setAuth);
  const setUser = useAuthStore((s) => s.setUser);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const setLoading = useAuthStore((s) => s.setLoading);

  return {
    user,
    isAuthenticated,
    isLoading,
    accessToken,
    setAuth,
    setUser,
    clearAuth,
    setLoading,
  };
}
