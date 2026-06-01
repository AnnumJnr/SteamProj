/**
 * types/api.ts
 * Shared API response shapes. Derived from backend DRF pagination and
 * custom_exception_handler in common/exceptions.py.
 */

// Matches Django REST Framework's StandardResultsPagination output
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Matches common/exceptions.py → custom_exception_handler output shape
export interface ApiError {
  detail?: string;
  message?: string;
  errors?: Record<string, string[]>;
  code?: string;
}

// Auth token pair
export interface TokenPair {
  access: string;
  refresh: string;
}

// Auth response — tokens are at the TOP LEVEL alongside user, not nested.
// Actual backend shape: { user: {...}, access: "...", refresh: "..." }
// Source: apps/users/views.py → RegisterView, LoginView, GoogleAuthView
export interface AuthResponse {
  user: import("./user").User;
  access: string;
  refresh: string;
}