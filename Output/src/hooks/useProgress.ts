/**
 * hooks/useProgress.ts
 * Responsibility: fetch and mutate user progress via TanStack Query.
 * Forbidden: store writes, navigation, analytics.
 * Includes unenrollCourse mutation — calls DELETE /progress/{course_id}/
 * Requires UnenrollCourseView added to backend progress/urls.py.
 */
 
"use client";
 
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/constants/queryKeys";
import * as progressService from "@/services/progressService";
 
export function useProgress(enabled = true) {
  return useQuery({
    queryKey: queryKeys.progress.list,
    queryFn: progressService.getProgress,
    enabled,
  });
}
 
export function useProgressSummary(enabled = true) {
  return useQuery({
    queryKey: queryKeys.progress.summary,
    queryFn: progressService.getProgressSummary,
    enabled,
  });
}
 
export function useStartCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => progressService.startCourse(courseId),
    onSuccess: (_, courseId) => {
      qc.invalidateQueries({ queryKey: queryKeys.progress.all });
      qc.invalidateQueries({ queryKey: queryKeys.progress.course(courseId) });
    },
  });
}
 
export function useCompleteCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => progressService.completeCourse(courseId),
    onSuccess: (_, courseId) => {
      qc.invalidateQueries({ queryKey: queryKeys.progress.all });
      qc.invalidateQueries({ queryKey: queryKeys.progress.course(courseId) });
      qc.invalidateQueries({ queryKey: queryKeys.combos.all });
    },
  });
}
 
// Unenroll = delete all progress for a course
// Calls DELETE /api/v1/progress/{course_id}/
export function useUnenrollCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => progressService.unenrollCourse(courseId),
    onSuccess: (_, courseId) => {
      qc.invalidateQueries({ queryKey: queryKeys.progress.all });
      qc.invalidateQueries({ queryKey: queryKeys.progress.course(courseId) });
      qc.invalidateQueries({ queryKey: queryKeys.combos.all });
    },
  });
}

export function useCourseProgress(courseId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.progress.course(courseId),
    queryFn: () => progressService.getCourseProgress(courseId),
    enabled: Boolean(courseId) && enabled,
  });
}