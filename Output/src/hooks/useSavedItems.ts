/**
 * hooks/useSavedItems.ts
 * Responsibility: fetch and mutate saved courses and combos via TanStack Query.
 * Forbidden: store writes, navigation, analytics.
  * IMPORTANT: unsaveCourse and unsaveCombo now take the COURSE/COMBO id,
 * not the saved-item record id. This matches the backend URL pattern:
 *   DELETE /progress/saved/courses/{course_id}/
 *   DELETE /progress/saved/combos/{combo_id}/
 * Source: apps/progress/urls.py
 */
 
"use client";
 
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/constants/queryKeys";
import * as progressService from "@/services/progressService";
 
export function useSavedCourses() {
  return useQuery({
    queryKey: queryKeys.saved.courses,
    queryFn: progressService.getSavedCourses,
  });
}
 
export function useSavedCombos() {
  return useQuery({
    queryKey: queryKeys.saved.combos,
    queryFn: progressService.getSavedCombos,
  });
}
 
export function useSaveCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => progressService.saveCourse(courseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.saved.courses });
    },
  });
}
 
// courseId = the actual course UUID (not the saved-item record id)
export function useUnsaveCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => progressService.unsaveCourse(courseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.saved.courses });
    },
  });
}
 
export function useSaveCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comboId: string) => progressService.saveCombo(comboId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.saved.combos });
    },
  });
}
 
// comboId = the actual combo UUID (not the saved-item record id)
export function useUnsaveCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comboId: string) => progressService.unsaveCombo(comboId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.saved.combos });
    },
  });
}