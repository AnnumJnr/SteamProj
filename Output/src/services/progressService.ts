/**
 * services/progressService.ts
 * All HTTP calls related to user progress and saved items.
 * Plain async functions — no state management, no analytics, no caching.
 * URL patterns verified against backend progress/urls.py:
 *
 * DELETE /progress/saved/courses/{course_id}/  — course_id is the COURSE uuid, not saved-item id
 * DELETE /progress/saved/combos/{combo_id}/    — combo_id is the COMBO uuid, not saved-item id
 * DELETE /progress/{course_id}/               — unenroll (delete all progress for a course)
 *
 * This was previously wrong — the frontend was passing saved-item record IDs
 * to endpoints that expect the actual course/combo IDs.
 */
 
import apiClient from "@/lib/api";
import type {
  UserProgress,
  ProgressSummary,
  SavedCourse,
  SavedCombo,
} from "@/types/progress";
import type { PaginatedResponse } from "@/types/api";
 
// ─── Progress ─────────────────────────────────────────────────────────────
 
// GET /api/v1/progress/
export async function getProgress(): Promise<PaginatedResponse<UserProgress>> {
  const response = await apiClient.get<PaginatedResponse<UserProgress>>("/progress/");
  return response.data;
}
 
// GET /api/v1/progress/summary/
export async function getProgressSummary(): Promise<ProgressSummary> {
  const response = await apiClient.get<ProgressSummary>("/progress/summary/");
  return response.data;
}
 
// POST /api/v1/progress/start/
export async function startCourse(courseId: string): Promise<UserProgress> {
  const response = await apiClient.post<UserProgress>("/progress/start/", {
    course_id: courseId,
  });
  return response.data;
}
 
// POST /api/v1/progress/complete/
export async function completeCourse(courseId: string): Promise<UserProgress> {
  const response = await apiClient.post<UserProgress>("/progress/complete/", {
    course_id: courseId,
  });
  return response.data;
}
 
// DELETE /api/v1/progress/{course_id}/
// Unenrolls the user from a course — deletes all progress for that course.
// Requires the UnenrollCourseView to be added to backend progress/urls.py.
export async function unenrollCourse(courseId: string): Promise<void> {
  await apiClient.delete(`/progress/${courseId}/`);
}
 
// ─── Saved Courses ────────────────────────────────────────────────────────
 
// GET /api/v1/progress/saved/courses/
export async function getSavedCourses(): Promise<PaginatedResponse<SavedCourse>> {
  const response = await apiClient.get<PaginatedResponse<SavedCourse>>(
    "/progress/saved/courses/"
  );
  return response.data;
}
 
// POST /api/v1/progress/saved/courses/
export async function saveCourse(courseId: string): Promise<SavedCourse> {
  const response = await apiClient.post<SavedCourse>("/progress/saved/courses/", {
    item_id: courseId,
  });
  return response.data;
}
 
// DELETE /api/v1/progress/saved/courses/{course_id}/
// Backend expects the COURSE id, not the saved-item record id.
// Source: progress/urls.py → saved/courses/<uuid:course_id>/
export async function unsaveCourse(courseId: string): Promise<void> {
  await apiClient.delete(`/progress/saved/courses/${courseId}/`);
}
 
// ─── Saved Combos ─────────────────────────────────────────────────────────
 
// GET /api/v1/progress/saved/combos/
export async function getSavedCombos(): Promise<PaginatedResponse<SavedCombo>> {
  const response = await apiClient.get<PaginatedResponse<SavedCombo>>(
    "/progress/saved/combos/"
  );
  return response.data;
}
 
// POST /api/v1/progress/saved/combos/
export async function saveCombo(comboId: string): Promise<SavedCombo> {
  const response = await apiClient.post<SavedCombo>("/progress/saved/combos/", {
    item_id: comboId,
  });
  return response.data;
}
 
// DELETE /api/v1/progress/saved/combos/{combo_id}/
// Backend expects the COMBO id, not the saved-item record id.
// Source: progress/urls.py → saved/combos/<uuid:combo_id>/
export async function unsaveCombo(comboId: string): Promise<void> {
  await apiClient.delete(`/progress/saved/combos/${comboId}/`);
}
 