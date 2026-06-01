/**
 * stores/authStore.ts
 * Authentication state store.
 *
 * setAuth() receives the user object and a TokenPair { access, refresh }.
 * The login/register pages construct that TokenPair from the flat backend
 * response: { user, access, refresh } → setAuth(user, { access, refresh })
 */

"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { wireAuthStore } from "@/lib/api";
import type { User } from "@/types/user";
import type { TokenPair } from "@/types/api";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setAuth: (user: User, tokens: TokenPair) => void;
  setUser: (user: User) => void;
  setTokens: (tokens: TokenPair) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      setAuth: (user, tokens) => {
        set({
          user,
          accessToken: tokens.access,
          refreshToken: tokens.refresh,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      setUser: (user) => set({ user }),

      setTokens: (tokens) =>
        set({
          accessToken: tokens.access,
          refreshToken: tokens.refresh,
        }),

      clearAuth: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
        }),

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: "stempath-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Wire auth store into Axios interceptors on module load
wireAuthStore({
  getAccessToken: () => useAuthStore.getState().accessToken,
  getRefreshToken: () => useAuthStore.getState().refreshToken,
  setTokens: (tokens) => useAuthStore.getState().setTokens(tokens),
  clearAuth: () => useAuthStore.getState().clearAuth(),
});