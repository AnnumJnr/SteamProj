/**
 * types/combo.ts
 * Derived from backend serializers exactly — Rule 10.
 *
 * IMPORTANT field name correction:
 * Backend ComboListSerializer and ComboDetailSerializer use:
 *   average_rating  (not rating_average)
 *   rating_count
 *   created_by_type (not created_by)
 *
 * Source: apps/combos/serializers.py → ComboListSerializer, ComboDetailSerializer
 */

import type { Course } from "./course";

export type ComboCreatedByType = "admin" | "system" | "user";

// Matches ComboCourseSerializer output (nested in ComboDetail)
// Source: apps/combos/serializers.py → ComboCourseSerializer
export interface ComboCourse {
  order: number;
  is_required: boolean;
  note: string | null;
  course: Course;
}

// Matches ComboListSerializer output
// Source: apps/combos/serializers.py → ComboListSerializer
export interface Combo {
  id: string;
  title: string;
  short_description: string;
  category: string;
  sub_category: string;
  difficulty: string;
  recommended_age: string;
  estimated_weeks: number;
  estimated_hours_per_week: number;
  is_featured: boolean;
  is_public: boolean;
  tags: string[];
  created_by_type: ComboCreatedByType;
  course_count: number;
  average_rating: number | null;  // annotated field — null when no ratings
  rating_count: number;
  created_at: string;
}

// Matches ComboDetailSerializer output (superset of ComboListSerializer)
// Source: apps/combos/serializers.py → ComboDetailSerializer
export interface ComboDetail extends Combo {
  full_description: string;
  overview: string;
  who_is_this_for: string;
  learning_outcomes: string[];
  prerequisites: string[];
  skills_gained: string[];
  learning_path_explanation: string;
  courses: ComboCourse[];
  updated_at: string;
}

// Matches ComboRatingSerializer output
// Source: apps/combos/serializers.py → ComboRatingSerializer
export interface ComboRating {
  id: string;
  user_email: string;
  rating: number;
  review: string;
  created_at: string;
}

// Payload for POST /api/v1/combos/ (create)
// Source: apps/combos/serializers.py → CreateComboSerializer
export interface CreateComboPayload {
  title: string;
  short_description?: string;
  full_description?: string;
  overview?: string;
  who_is_this_for?: string;
  learning_outcomes?: string[];
  prerequisites?: string[];
  skills_gained?: string[];
  category?: string;
  sub_category?: string;
  difficulty?: string;
  recommended_age?: string;
  estimated_weeks?: number;
  estimated_hours_per_week?: number;
  learning_path_explanation?: string;
  is_public?: boolean;
  tags?: string[];
  courses?: Array<{
    course_id: string;
    order?: number;
    is_required?: boolean;
    note?: string;
  }>;
}

// Payload for PATCH /api/v1/combos/:id/
// Source: apps/combos/serializers.py → UpdateComboSerializer
export interface UpdateComboPayload extends Partial<CreateComboPayload> {
  is_featured?: boolean;
}

// Query params for GET /api/v1/combos/
export interface ComboFilters {
  category?: string;
  difficulty?: string;
  recommended_age?: string;
  search?: string;
  page?: number;
}

// Combo progress — returned by GET /api/v1/combos/:id/progress/
// Source: apps/combos/services.py → get_combo_progress()
export interface ComboProgress {
  combo_id?: string;
  total_courses: number;
  completed_courses: number;
  completion_percentage: number;
  completed_course_ids: string[];
}