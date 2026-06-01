/**
 * services/authService.ts
 * All HTTP calls related to authentication.
 *
 * IMPORTANT — Backend response shape for login/register/google:
 *   { "user": {...}, "access": "...", "refresh": "..." }
 *   Tokens are at the TOP LEVEL — not nested under a "tokens" key.
 *   Source: apps/users/views.py → LoginView, RegisterView, GoogleAuthView
 */

import apiClient from "@/lib/api";
import type { AuthResponse, TokenPair } from "@/types/api";
import type { User, UpdateProfilePayload } from "@/types/user";
 
// POST /api/v1/auth/register/
export async function register(payload: {
  email: string;
  password: string;
  password_confirm: string;
  display_name?: string;
}): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/auth/register/", payload);
  return response.data;
}
 
// POST /api/v1/auth/login/
export async function login(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/auth/login/", payload);
  return response.data;
}
 
// POST /api/v1/auth/logout/
export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post("/auth/logout/", { refresh: refreshToken });
}
 
// POST /api/v1/auth/token/refresh/
export async function refreshToken(refresh: string): Promise<TokenPair> {
  const response = await apiClient.post<TokenPair>("/auth/token/refresh/", {
    refresh,
  });
  return response.data;
}
 
// POST /api/v1/auth/google/
export async function googleAuth(idToken: string): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/auth/google/", {
    id_token: idToken,
  });
  return response.data;
}
 
// GET /api/v1/auth/me/
export async function getMe(): Promise<User> {
  const response = await apiClient.get<User>("/auth/me/");
  return response.data;
}
 
// PATCH /api/v1/auth/me/
export async function updateProfile(payload: UpdateProfilePayload): Promise<User> {
  const response = await apiClient.patch<User>("/auth/me/", payload);
  return response.data;
}
 