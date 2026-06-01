/**
 * lib/api.ts
 * Single Axios HTTP client for all backend communication.
 * All services import from this file. No component calls Axios directly.
 *
 * Interceptor flow:
 *   Request  → attach access token from authStore
 *   Response → on 401: silent refresh → retry → if still 401: clearAuth + redirect
 */

import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { ApiError, TokenPair } from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

// ─── Axios Instance ────────────────────────────────────────────────────────

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: false, // JWT via Authorization header, not cookies
});

// ─── Token Helpers ─────────────────────────────────────────────────────────
// Access auth store tokens without importing the store directly here.
// The store sets these via the functions below, which the interceptors call.

let _getAccessToken: (() => string | null) | null = null;
let _getRefreshToken: (() => string | null) | null = null;
let _setTokens: ((tokens: TokenPair) => void) | null = null;
let _clearAuth: (() => void) | null = null;

/**
 * Called once from the auth store initialisation.
 * Wires the auth store's token accessors into this module.
 */
export function wireAuthStore(config: {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  setTokens: (tokens: TokenPair) => void;
  clearAuth: () => void;
}) {
  _getAccessToken = config.getAccessToken;
  _getRefreshToken = config.getRefreshToken;
  _setTokens = config.setTokens;
  _clearAuth = config.clearAuth;
}

// ─── Request Interceptor ───────────────────────────────────────────────────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = _getAccessToken?.();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor — Silent Refresh ─────────────────────────────────

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Only attempt refresh on 401, and only once per request
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(normaliseError(error));
    }

    if (isRefreshing) {
      // Queue this request until the refresh completes
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
          }
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = _getRefreshToken?.();

    if (!refreshToken) {
      // No refresh token — clear auth and redirect to login
      _clearAuth?.();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return Promise.reject(normaliseError(error));
    }

    try {
      // Attempt silent token refresh
      const response = await axios.post<TokenPair>(
        `${API_BASE_URL}/auth/token/refresh/`,
        { refresh: refreshToken }
      );

      const newTokens = response.data;
      _setTokens?.(newTokens);
      processQueue(null, newTokens.access);

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newTokens.access}`;
      }

      return apiClient(originalRequest);
    } catch (refreshError) {
      // Refresh failed — session is dead
      processQueue(refreshError, null);
      _clearAuth?.();

      // FALLBACK: Silent refresh failed — redirect to login
      // PRIMARY: lib/api.ts → response interceptor silent refresh
      // CONDITION: Refresh token is expired or invalid
      // ACTION: Clear auth state and redirect to login page
      // THRESHOLD: Every occurrence is a legitimate session expiry — no investigation needed
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }

      return Promise.reject(normaliseError(refreshError as AxiosError));
    } finally {
      isRefreshing = false;
    }
  }
);

// ─── Error Normaliser ──────────────────────────────────────────────────────

/**
 * Transforms Axios errors into a consistent ApiError shape.
 * Matches the output of common/exceptions.py → custom_exception_handler.
 */
export function normaliseError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data) {
      return {
        detail: data.detail || data.message,
        message: data.message || data.detail,
        errors: data.errors,
        code: data.code,
      };
    }
    return {
      detail: error.message,
      message: error.message,
    };
  }
  return { detail: "An unexpected error occurred.", message: "An unexpected error occurred." };
}

export default apiClient;
