/**
 * services/comboService.ts
 * All HTTP calls related to combos.
 * Plain async functions — no state management, no analytics, no caching.
 * Removing a course from a combo uses PATCH /combos/{id}/ with a new courses array
 * — there is no dedicated remove-course endpoint.
 * Source: apps/combos/services.py → update_combo() replaces entire course list.
 * Course removal uses the dedicated endpoint:
 *   DELETE /combos/{combo_id}/courses/{course_id}/
 * Source: apps/combos/urls.py → combo-course-detail
 * Source: apps/combos/views.py → ComboCourseDetailView
 *
 * This requires remove_course_from_combo to be properly defined
 * as a method inside ComboService in services.py (not in a comment block).
 */
 
import apiClient from "@/lib/api";
import type {
  Combo,
  ComboDetail,
  ComboFilters,
  ComboProgress,
  ComboRating,
  CreateComboPayload,
  UpdateComboPayload,
} from "@/types/combo";
import type { PaginatedResponse } from "@/types/api";
 
// GET /api/v1/combos/
export async function getCombos(
  filters: ComboFilters = {}
): Promise<PaginatedResponse<Combo>> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== "")
  );
  const response = await apiClient.get<PaginatedResponse<Combo>>("/combos/", { params });
  return response.data;
}
 
// GET /api/v1/combos/{id}/
export async function getCombo(id: string): Promise<ComboDetail> {
  const response = await apiClient.get<ComboDetail>(`/combos/${id}/`);
  return response.data;
}
 
// POST /api/v1/combos/
export async function createCombo(payload: CreateComboPayload): Promise<ComboDetail> {
  const response = await apiClient.post<ComboDetail>("/combos/", payload);
  return response.data;
}
 
// PATCH /api/v1/combos/{id}/
// Used for: editing title/description/metadata, toggling is_public,
// and replacing the entire course list when adding courses.
export async function updateCombo(
  id: string,
  payload: UpdateComboPayload
): Promise<ComboDetail> {
  const response = await apiClient.patch<ComboDetail>(`/combos/${id}/`, payload);
  return response.data;
}
 
// DELETE /api/v1/combos/{id}/
export async function deleteCombo(id: string): Promise<void> {
  await apiClient.delete(`/combos/${id}/`);
}
 
// GET /api/v1/combos/mine/
export async function getMyCombos(): Promise<PaginatedResponse<Combo>> {
  const response = await apiClient.get<PaginatedResponse<Combo>>("/combos/mine/");
  return response.data;
}
 
// GET /api/v1/combos/{id}/progress/
export async function getComboProgress(id: string): Promise<ComboProgress> {
  const response = await apiClient.get<ComboProgress>(`/combos/${id}/progress/`);
  return response.data;
}
 
// POST /api/v1/combos/{id}/rate/
export async function rateCombo(id: string, rating: number): Promise<ComboRating> {
  const response = await apiClient.post<ComboRating>(`/combos/${id}/rate/`, { rating });
  return response.data;
}
 
// DELETE /api/v1/combos/{id}/rate/
export async function removeComboRating(id: string): Promise<void> {
  await apiClient.delete(`/combos/${id}/rate/`);
}
 
// GET /api/v1/combos/{id}/ratings/
export async function getComboRatings(id: string): Promise<PaginatedResponse<ComboRating>> {
  const response = await apiClient.get<PaginatedResponse<ComboRating>>(`/combos/${id}/ratings/`);
  return response.data;
}
 
/**
 * Remove a single course from a combo.
 * Calls DELETE /combos/{combo_id}/courses/{course_id}/
 * Source: apps/combos/urls.py → combo-course-detail
 * Requires remove_course_from_combo to be active in services.py.
 */
export async function removeCourseFromCombo(
  comboId: string,
  courseId: string
): Promise<void> {
  await apiClient.delete(`/combos/${comboId}/courses/${courseId}/`);
}
 
/**
 * Add courses to a combo by sending the full updated course list.
 * The backend replaces the entire course list when courses is provided.
 * Source: apps/combos/services.py → update_combo()
 *
 * @param comboId - combo to update
 * @param existingCourses - current courses array from ComboDetail
 * @param newCourseIds - array of course IDs to append
 */
export async function addCoursesToCombo(
  comboId: string,
  existingCourses: Array<{ course: { id: string }; order: number; is_required: boolean; note: string | null }>,
  newCourseIds: string[]
): Promise<ComboDetail> {
  const existingList = existingCourses.map((cc, index) => ({
    course_id: cc.course.id,
    order: index + 1,
    is_required: cc.is_required,
    note: cc.note || undefined,
  }));
 
  const newList = newCourseIds.map((courseId, index) => ({
    course_id: courseId,
    order: existingList.length + index + 1,
    is_required: true,
  }));
 
  const response = await apiClient.patch<ComboDetail>(`/combos/${comboId}/`, {
    courses: [...existingList, ...newList],
  });
  return response.data;
}
 