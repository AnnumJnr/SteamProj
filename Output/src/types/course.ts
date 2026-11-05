/**
 * types/course.ts
 * Derived from backend serializers exactly — Rule 10.
 * Source: apps/courses/serializers.py → CourseListSerializer, CourseDetailSerializer
 */

export type CourseProvider =
  | "YouTube"
  | "freeCodeCamp"
  | "MIT OCW"
  | "OpenStax"
  | "CK-12"
  | "Khan Academy";

export type CourseProviderType =
  | "video_platform"
  | "learning_platform"
  | "university"
  | "open_textbook";

export type CourseLevel = "Beginner" | "Intermediate" | "Advanced";

export type CourseAgeGroup = "Kids" | "Teens" | "Adults";

export type CourseFormat = "Video" | "Text" | "Interactive";

// Matches CourseVideoItemSerializer output (nested in CourseDetail only)
// Source: apps/courses/serializers.py → CourseVideoItemSerializer
export interface CourseVideoItem {
  id: string;
  video_id: string;
  title: string;
  position: number;
  thumbnail_url: string;
  duration_seconds: number | null;
  published_at: string | null;
}

// Matches CourseListSerializer output
// Source: apps/courses/serializers.py → CourseListSerializer
export interface Course {
  id: string;
  title: string;
  short_description: string;
  provider: CourseProvider;
  provider_type: CourseProviderType;
  source_url: string;
  category: string;
  sub_category: string;
  level: CourseLevel;
  age_group: CourseAgeGroup;
  format: CourseFormat;
  duration_hours: number;
  duration_minutes: number;
  thumbnail_url: string | null;
  is_free: boolean;
  rating_average: number;
  rating_count: number;
  tags: string[];
  /** Video gate: true only when the requesting user has started the course. */
  video_access_granted: boolean;
}

// Matches CourseDetailSerializer output (superset of CourseListSerializer)
// Source: apps/courses/serializers.py → CourseDetailSerializer
export interface CourseDetail extends Course {
  full_description: string;
  learning_outcomes: string[];
  prerequisites: string[];
  instructor: string | null;
  certificate_available: boolean;
  language: string;
  created_at: string;
  updated_at: string;
  /**
   * Stored playlist videos, in playlist order. Empty until the user starts
   * the course (gate unlocked) and ingestion has populated the playlist.
   * source_url IS served for unlocked YouTube courses — used as fallback
   * embed player when videos is empty.
   */
  videos: CourseVideoItem[];
}

// Query params for GET /api/v1/courses/
export interface CourseFilters {
  category?: string;
  level?: string;
  age_group?: string;
  provider?: string;
  format?: string;
  search?: string;
  page?: number;
}
