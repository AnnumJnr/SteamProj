/**
 * hooks/useCourses.ts
 * Responsibility: fetch and cache course data via TanStack Query.
 * Forbidden: store writes, navigation, analytics.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/constants/queryKeys";
import * as courseService from "@/services/courseService";
import type { CourseFilters } from "@/types/course";

export function useCourses(filters: CourseFilters = {}) {
  return useQuery({
    queryKey: queryKeys.courses.list(filters),
    queryFn: () => courseService.getCourses(filters),
  });
}

export function useCourse(id: string) {
  return useQuery({
    queryKey: queryKeys.courses.detail(id),
    queryFn: () => courseService.getCourse(id),
    enabled: Boolean(id),
  });
}
