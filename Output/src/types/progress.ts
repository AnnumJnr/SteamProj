/**
 * types/progress.ts
 * Derived from backend serializers exactly — Rule 10.
 * Source: apps/progress/serializers.py → UserProgressSerializer,
 *         ProgressSummarySerializer, SavedCourseSerializer, SavedComboSerializer
 */

import type { Course } from "./course";
import type { Combo } from "./combo";

export type ProgressStatus = "not_started" | "in_progress" | "completed";

export type SavedItemType = "course" | "combo";

// Matches UserProgressSerializer output
// Source: apps/progress/serializers.py → UserProgressSerializer
export interface UserProgress {
  id: string;
  course: Course;
  status: ProgressStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// Matches ProgressSummarySerializer output
// Source: apps/progress/serializers.py → ProgressSummarySerializer
export interface ProgressSummary {
  not_started: number;
  in_progress: number;
  completed: number;
  total: number;
}

// Matches SavedCourseSerializer output
// Source: apps/progress/serializers.py → SavedCourseSerializer
export interface SavedCourse {
  id: string;
  course: Course;
  saved_at: string;
}

// Matches SavedComboSerializer output
// Source: apps/progress/serializers.py → SavedComboSerializer
export interface SavedCombo {
  id: string;
  combo: Combo;
  saved_at: string;
}
