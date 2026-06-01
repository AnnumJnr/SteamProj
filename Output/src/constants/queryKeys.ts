/**
 * constants/queryKeys.ts
 * TanStack Query key factory.
 * All query keys live here. Never hardcode query keys in hooks.
 * Structured as nested factories to enable precise cache invalidation.
 */

import type { CourseFilters } from "@/types/course";
import type { ComboFilters } from "@/types/combo";

export const queryKeys = {
  // ─── Courses ───────────────────────────────────────────────────────────────
  courses: {
    all: ["courses"] as const,
    list: (filters: CourseFilters) => ["courses", "list", filters] as const,
    detail: (id: string) => ["courses", "detail", id] as const,
  },

  // ─── Combos ───────────────────────────────────────────────────────────────
  combos: {
    all: ["combos"] as const,
    list: (filters: ComboFilters) => ["combos", "list", filters] as const,
    detail: (id: string) => ["combos", "detail", id] as const,
    mine: ["combos", "mine"] as const,
    progress: (id: string) => ["combos", "progress", id] as const,
    ratings: (id: string) => ["combos", "ratings", id] as const,
  },

  // ─── Progress ─────────────────────────────────────────────────────────────
  progress: {
    all: ["progress"] as const,
    list: ["progress", "list"] as const,
    summary: ["progress", "summary"] as const,
  },

  // ─── Saved Items ──────────────────────────────────────────────────────────
  saved: {
    courses: ["saved", "courses"] as const,
    combos: ["saved", "combos"] as const,
  },

  // ─── Auth ─────────────────────────────────────────────────────────────────
  auth: {
    me: ["auth", "me"] as const,
  },
} as const;
