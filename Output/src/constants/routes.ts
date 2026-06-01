/**
 * constants/routes.ts
 * All client-side route paths as constants.
 * Never hardcode route strings in components or hooks.
 */

export const ROUTES = {
  // Public routes
  HOME: "/",
  COURSES: "/courses",
  COURSE_DETAIL: (id: string) => `/courses/${id}`,
  COMBOS: "/combos",
  COMBO_DETAIL: (id: string) => `/combos/${id}`,
  COMBO_CREATE: "/combos/create",
  SEARCH: "/search",

  // Auth routes
  LOGIN: "/login",
  REGISTER: "/register",

  // Protected routes
  DASHBOARD: "/dashboard",
  DASHBOARD_PROGRESS: "/dashboard/progress",
  DASHBOARD_SAVED: "/dashboard/saved",
} as const;
