/**
 * services/courseService.ts
 * All HTTP calls related to courses.
 * Plain async functions — no state management, no analytics, no caching.
 */

import apiClient from "@/lib/api";
import type { Course, CourseDetail, CourseFilters } from "@/types/course";
import type { PaginatedResponse } from "@/types/api";

// GET /api/v1/courses/
// Supports filter params: category, level, age_group, provider, format, search, page
export async function getCourses(
  filters: CourseFilters = {}
): Promise<PaginatedResponse<Course>> {
  // Strip undefined values so they don't appear as empty query params
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== "")
  );
  const response = await apiClient.get<PaginatedResponse<Course>>("/courses/", {
    params,
  });
  return response.data;
}

// GET /api/v1/courses/:id/
export async function getCourse(id: string): Promise<CourseDetail> {
  const response = await apiClient.get<CourseDetail>(`/courses/${id}/`);
  return response.data;
}
