/**
 * constants/events.ts
 * Analytics event name constants for frontend-owned events.
 *
 * CRITICAL: These string values must match apps/analytics/events.py exactly.
 * Any mismatch will cause PostHog to record duplicate or orphaned event streams.
 *
 * OWNER SPLIT:
 *   Frontend fires:  COURSE_VIEWED, COMBO_VIEWED, SEARCH_PERFORMED, FILTER_APPLIED
 *   Backend fires:   USER_SIGNED_UP, USER_LOGGED_IN, USER_PROFILE_UPDATED,
 *                    COURSE_STARTED, COURSE_COMPLETED, COMBO_STARTED,
 *                    COMBO_PROGRESS_UPDATED, COMBO_COMPLETED, COMBO_CREATED
 */

// ─── Frontend-owned events ────────────────────────────────────────────────────
// OWNER: frontend
// FIRED FROM: see each event comment

export const EVENTS = {
  // FIRED FROM: src/app/courses/[id]/page.tsx — on component mount
  COURSE_VIEWED: "course_viewed",

  // FIRED FROM: src/app/combos/[id]/page.tsx — on component mount
  COMBO_VIEWED: "combo_viewed",

  // FIRED FROM: src/app/search/page.tsx — on query submission
  SEARCH_PERFORMED: "search_performed",

  // FIRED FROM: src/components/course/CourseFilters.tsx — on filter change
  FILTER_APPLIED: "filter_applied",
} as const;

export type FrontendEventName = (typeof EVENTS)[keyof typeof EVENTS];
