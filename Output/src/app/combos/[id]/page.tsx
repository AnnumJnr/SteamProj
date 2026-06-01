/**
 * app/combos/[id]/page.tsx
 * Combo detail page with progress tracking and save button.
 *
 * Two distinct modes depending on who is viewing:
 *
 * VIEWER MODE (public combo or non-owner):
 *   - Full combo info display (title, description, who-is-this-for, outcomes, skills, courses)
 *   - Progress tracking
 *   - Save / Unsave
 *
 * OWNER MODE (private combo, authenticated owner):
 *   - Everything in viewer mode
 *   - Edit panel: title, short description, category, difficulty, visibility toggle
 *   - Course management: add courses from search, remove individual courses, reorder
 *   - Publish / Make private toggle
 *   - Delete combo
 *
 * The short_description is shown prominently for user-created combos
 * where overview/full_description may be empty.
 */
 
"use client";
 
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useCombo, useComboProgress, useDeleteCombo, useUpdateCombo } from "@/hooks/useCombos";
import { useCompleteCourse, useStartCourse } from "@/hooks/useProgress";
import { useSaveCombo, useSavedCombos, useUnsaveCombo } from "@/hooks/useSavedItems";
import { useCourses } from "@/hooks/useCourses";
import { useAuth } from "@/hooks/useAuth";
import { PageContainer } from "@/components/layout/PageContainer";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { ROUTES } from "@/constants/routes";
import { STEM_CATEGORIES, COMBO_DIFFICULTIES } from "@/constants/filters";
import { formatRating, formatRatingCount, cn } from "@/lib/utils";
import * as comboService from "@/services/comboService";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/constants/queryKeys";
import type { Course } from "@/types/course";
 
// ─── Helper: difficulty badge variant ────────────────────────────────────────
function difficultyVariant(d: string): "success" | "warning" | "danger" | "muted" {
  if (d === "Beginner") return "success";
  if (d === "Intermediate") return "warning";
  if (d === "Advanced") return "danger";
  return "muted";
}
 
export default function ComboDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { isAuthenticated, user } = useAuth();
  const qc = useQueryClient();
 
  const { data: combo, isLoading, isError, refetch } = useCombo(id);
  const { data: progress } = useComboProgress(id);
  const { mutate: deleteCombo, isPending: isDeleting } = useDeleteCombo();
  const { mutate: updateCombo, isPending: isUpdating } = useUpdateCombo(id);
  const { mutate: startCourse } = useStartCourse();
  const { mutate: completeCourse } = useCompleteCourse();
  const { mutate: saveCombo, isPending: isSaving } = useSaveCombo();
  const { mutate: unsaveCombo, isPending: isUnsaving } = useUnsaveCombo();
  const { data: savedCombosData } = useSavedCombos();
 
  // ─── Owner edit state ─────────────────────────────────────────────────────
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isAddCoursesOpen, setIsAddCoursesOpen] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
 
  // Edit form fields
  const [editTitle, setEditTitle] = useState("");
  const [editShortDesc, setEditShortDesc] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editDifficulty, setEditDifficulty] = useState("");
  const [editRecommendedAge, setEditRecommendedAge] = useState("");
 
  // Course search for add-courses panel
  const [courseSearch, setCourseSearch] = useState("");
  const [committedSearch, setCommittedSearch] = useState("");
  const [removingCourseId, setRemovingCourseId] = useState<string | null>(null);
  const [addingCourseId, setAddingCourseId] = useState<string | null>(null);
 
  const { data: searchResults, isLoading: searchLoading } = useCourses({
    search: committedSearch || undefined,
    page: 1,
  });
 
  const [actionMessage, setActionMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
 
  // ─── Derived state ────────────────────────────────────────────────────────
  const isSaved = savedCombosData?.results?.some((s) => s.combo.id === id) ?? false;
 
  // Owner = authenticated AND this combo was created by a user AND the user
  // has access to edit it (backend enforces the actual permission check).
  // We show owner controls if created_by_type === "user" and user is authenticated.
  const isOwner = isAuthenticated && combo?.created_by_type === "user";
 
  const courses = combo?.courses ?? [];
  const completedIds = new Set(progress?.completed_course_ids ?? []);
  const completionPct = progress?.completion_percentage ?? 0;
 
  // Courses already in this combo — used to exclude from add-courses search
  const existingCourseIds = new Set(courses.map((cc) => cc.course?.id).filter(Boolean));
 
  // Available courses to add (exclude already added ones)
  const availableCourses = (searchResults?.results ?? []).filter(
    (c) => !existingCourseIds.has(c.id)
  );
 
  // ─── Populate edit form when combo loads ─────────────────────────────────
  useEffect(() => {
    if (combo) {
      setEditTitle(combo.title);
      setEditShortDesc(combo.short_description || "");
      setEditCategory(combo.category || "");
      setEditDifficulty(combo.difficulty || "");
      setEditRecommendedAge(combo.recommended_age || "");
    }
  }, [combo]);
 
  // ─── Analytics ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!combo) return;
    if (typeof window !== "undefined" && (window as unknown as { posthog?: { capture: (e: string, p: Record<string, unknown>) => void } }).posthog) {
      (window as unknown as { posthog: { capture: (e: string, p: Record<string, unknown>) => void } }).posthog.capture("combo_viewed", {
        combo_id: combo.id, combo_title: combo.title, category: combo.category,
      });
    }
  }, [combo]);
 
  // ─── Helpers ─────────────────────────────────────────────────────────────
  function showMessage(text: string, type: "success" | "error" = "success") {
    setActionMessage({ text, type });
    setTimeout(() => setActionMessage(null), 3500);
  }
 
  // ─── Edit save ────────────────────────────────────────────────────────────
  function handleSaveEdit() {
    if (!editTitle.trim()) { showMessage("Title cannot be empty.", "error"); return; }
    updateCombo(
      {
        title: editTitle.trim(),
        short_description: editShortDesc.trim(),
        category: editCategory,
        difficulty: editDifficulty,
        recommended_age: editRecommendedAge || undefined,
      },
      {
        onSuccess: () => { showMessage("Combo updated successfully."); setIsEditOpen(false); },
        onError: () => showMessage("Failed to save changes.", "error"),
      }
    );
  }
 
  // ─── Publish / Make private ───────────────────────────────────────────────
  function handleTogglePublic() {
    if (!combo) return;
    const newValue = !combo.is_public;
    updateCombo(
      { is_public: newValue },
      {
        onSuccess: () => showMessage(newValue ? "Combo is now public." : "Combo is now private."),
        onError: () => showMessage("Failed to update visibility.", "error"),
      }
    );
  }
 
  // ─── Delete ──────────────────────────────────────────────────────────────
  function handleDeleteCombo() {
    deleteCombo(id, {
      onSuccess: () => router.push(ROUTES.COMBOS),
    });
  }
 
  // ─── Remove course ────────────────────────────────────────────────────────
  async function handleRemoveCourse(courseId: string) {
    setRemovingCourseId(courseId);
    try {
      await comboService.removeCourseFromCombo(id, courseId);
      qc.invalidateQueries({ queryKey: queryKeys.combos.detail(id) });
      showMessage("Course removed.");
    } catch {
      showMessage("Failed to remove course.", "error");
    } finally {
      setRemovingCourseId(null);
    }
  }
 
  // ─── Add course ───────────────────────────────────────────────────────────
  async function handleAddCourse(course: Course) {
    if (!combo) return;
    setAddingCourseId(course.id);
    try {
      await comboService.addCoursesToCombo(id, combo.courses ?? [], [course.id]);
      qc.invalidateQueries({ queryKey: queryKeys.combos.detail(id) });
      showMessage(`"${course.title}" added to combo.`);
    } catch {
      showMessage("Failed to add course.", "error");
    } finally {
      setAddingCourseId(null);
    }
  }
 
  // ─── Reorder (move up/down via full course list PATCH) ────────────────────
  async function handleMoveCourse(index: number, direction: "up" | "down") {
    if (!combo) return;
    const list = [...(combo.courses ?? [])];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= list.length) return;
    [list[index], list[targetIndex]] = [list[targetIndex], list[index]];
 
    const payload = list.map((cc, i) => ({
      course_id: cc.course.id,
      order: i + 1,
      is_required: cc.is_required,
      note: cc.note || undefined,
    }));
 
    try {
      await comboService.updateCombo(id, { courses: payload });
      qc.invalidateQueries({ queryKey: queryKeys.combos.detail(id) });
    } catch {
      showMessage("Failed to reorder courses.", "error");
    }
  }
 
  // ─── Loading / error states ───────────────────────────────────────────────
  if (isLoading) return <LoadingState message="Loading combo path..." className="py-24" />;
  if (isError || !combo) {
    return <PageContainer><ErrorState title="Combo not found" onRetry={() => refetch()} /></PageContainer>;
  }
 
  // The description to show — prefer short_description which is always populated,
  // fall back to overview for curated combos that use that field instead.
  const displayDescription = combo.short_description || combo.overview || "";
 
  return (
    <PageContainer>
      <div className="py-8">
 
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-text-muted mb-6">
          <Link href={ROUTES.COMBOS} className="hover:text-primary transition-colors">Combo Paths</Link>
          <span>/</span>
          <span className="text-text-secondary truncate max-w-xs">{combo.title}</span>
        </nav>
 
        {/* Action feedback banner */}
        {actionMessage && (
          <div className={cn(
            "mb-4 px-4 py-3 rounded-lg text-sm border",
            actionMessage.type === "success"
              ? "bg-accent-muted border-accent/20 text-accent"
              : "bg-danger/10 border-danger/30 text-danger"
          )}>
            {actionMessage.text}
          </div>
        )}
 
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
 
          {/* ─── Left: Main content ──────────────────────────────────── */}
          <div className="lg:col-span-2 space-y-8">
 
            {/* Header */}
            <div>
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  {combo.category && <Badge variant="primary">{combo.category}</Badge>}
                  <Badge variant={difficultyVariant(combo.difficulty)}>{combo.difficulty}</Badge>
                  {combo.recommended_age && combo.recommended_age !== "All Ages" && (
                    <Badge variant="muted">{combo.recommended_age}</Badge>
                  )}
                  {combo.is_featured && <Badge variant="warning">Featured</Badge>}
                  {!combo.is_public && <Badge variant="muted">Private</Badge>}
                  {combo.is_public && !combo.is_featured && <Badge variant="success">Public</Badge>}
                </div>
 
                {/* Owner controls */}
                {isOwner && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button variant="secondary" size="sm" onClick={() => setIsEditOpen(!isEditOpen)}>
                      {isEditOpen ? "Close Editor" : "Edit Combo"}
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => setShowDeleteModal(true)}>
                      Delete
                    </Button>
                  </div>
                )}
              </div>
 
              <h1 className="text-2xl font-bold text-text-primary mb-2">{combo.title}</h1>
 
              {/* Description — always shown, uses short_description or overview */}
              {displayDescription && (
                <p className="text-sm text-text-secondary leading-relaxed">{displayDescription}</p>
              )}
            </div>
 
            {/* ─── Owner Edit Panel ─────────────────────────────────── */}
            {isOwner && isEditOpen && (
              <Card className="p-6 border-primary/30 bg-primary-subtle/20 space-y-5">
                <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
                  <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit Combo Details
                </h2>
 
                <Input
                  label="Title"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="Combo title"
                />
 
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-text-primary">Description</label>
                  <textarea
                    value={editShortDesc}
                    onChange={(e) => setEditShortDesc(e.target.value)}
                    placeholder="What will learners gain from this combo path?"
                    rows={3}
                    className="w-full px-3 py-2 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors resize-none"
                  />
                </div>
 
                {/* Category */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-text-primary">Category</label>
                  <div className="grid grid-cols-2 gap-2">
                    {STEM_CATEGORIES.map((cat) => (
                      <button
                        key={cat.value}
                        type="button"
                        onClick={() => setEditCategory(cat.value)}
                        className={cn(
                          "px-3 py-2 rounded-lg text-sm text-left transition-all",
                          editCategory === cat.value
                            ? "bg-primary-subtle border border-primary/40 text-primary font-medium"
                            : "bg-surface-overlay border border-surface-border text-text-secondary hover:border-primary/30"
                        )}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>
 
                {/* Difficulty */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-text-primary">Difficulty</label>
                  <div className="flex gap-2">
                    {COMBO_DIFFICULTIES.map((d) => (
                      <button
                        key={d.value}
                        type="button"
                        onClick={() => setEditDifficulty(d.value)}
                        className={cn(
                          "flex-1 py-2 rounded-lg text-sm transition-all",
                          editDifficulty === d.value
                            ? "bg-primary-subtle border border-primary/40 text-primary font-medium"
                            : "bg-surface-overlay border border-surface-border text-text-secondary hover:border-primary/30"
                        )}
                      >
                        {d.label}
                      </button>
                    ))}
                  </div>
                </div>
 
                {/* Visibility toggle */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface-overlay border border-surface-border">
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {combo.is_public ? "Public" : "Private"}
                    </p>
                    <p className="text-xs text-text-muted">
                      {combo.is_public
                        ? "Anyone can find and view this combo. Others can rate it."
                        : "Only you can see this combo."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleTogglePublic}
                    className={cn(
                      "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 flex-shrink-0",
                      combo.is_public ? "bg-primary" : "bg-surface-border"
                    )}
                    role="switch"
                    aria-checked={combo.is_public}
                  >
                    <span
                      className={cn(
                        "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200",
                        combo.is_public ? "translate-x-6" : "translate-x-1"
                      )}
                    />
                  </button>
                </div>
 
                <div className="flex gap-3 justify-end pt-2 border-t border-surface-border">
                  <Button variant="ghost" onClick={() => setIsEditOpen(false)}>Cancel</Button>
                  <Button isLoading={isUpdating} onClick={handleSaveEdit}>Save Changes</Button>
                </div>
              </Card>
            )}
 
            {/* ─── Who is this for ─────────────────────────────────── */}
            {combo.who_is_this_for && (
              <div className="p-4 rounded-xl bg-primary-subtle border border-primary/20">
                <h3 className="text-sm font-semibold text-primary mb-1">Who is this for?</h3>
                <p className="text-sm text-text-secondary">{combo.who_is_this_for}</p>
              </div>
            )}
 
            {/* ─── Learning outcomes ───────────────────────────────── */}
            {combo.learning_outcomes?.length > 0 && (
              <div>
                <h2 className="text-base font-semibold text-text-primary mb-3">What you will learn</h2>
                <ul className="space-y-2">
                  {combo.learning_outcomes.map((outcome, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-text-secondary">
                      <svg className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      {outcome}
                    </li>
                  ))}
                </ul>
              </div>
            )}
 
            {/* ─── Skills gained ───────────────────────────────────── */}
            {combo.skills_gained?.length > 0 && (
              <div>
                <h2 className="text-base font-semibold text-text-primary mb-3">Skills you will gain</h2>
                <div className="flex flex-wrap gap-2">
                  {combo.skills_gained.map((skill) => (
                    <span key={skill} className="px-3 py-1 text-xs rounded-full bg-accent-muted text-accent border border-accent/20 font-medium">{skill}</span>
                  ))}
                </div>
              </div>
            )}
 
            {/* ─── Course sequence ─────────────────────────────────── */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-text-primary">
                  Course sequence ({courses.length} courses)
                </h2>
                {/* Add courses button — owner only */}
                {isOwner && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setIsAddCoursesOpen(!isAddCoursesOpen)}
                  >
                    {isAddCoursesOpen ? "Close" : "+ Add Courses"}
                  </Button>
                )}
              </div>
 
              {/* Add courses panel — owner only */}
              {isOwner && isAddCoursesOpen && (
                <Card className="p-4 mb-4 border-primary/20 bg-primary-subtle/10">
                  <h3 className="text-sm font-semibold text-text-primary mb-3">Search and add courses</h3>
                  <form
                    onSubmit={(e) => { e.preventDefault(); setCommittedSearch(courseSearch.trim()); }}
                    className="flex gap-2 mb-3"
                  >
                    <input
                      type="search"
                      value={courseSearch}
                      onChange={(e) => setCourseSearch(e.target.value)}
                      placeholder="Search courses by title or category..."
                      className="flex-1 px-3 py-2 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                    />
                    <Button type="submit" size="sm">Search</Button>
                  </form>
 
                  {committedSearch && (
                    <button
                      type="button"
                      onClick={() => { setCourseSearch(""); setCommittedSearch(""); }}
                      className="text-xs text-primary mb-2 hover:text-primary-hover"
                    >
                      Clear search
                    </button>
                  )}
 
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {searchLoading ? (
                      <div className="flex items-center justify-center py-4">
                        <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : availableCourses.length === 0 ? (
                      <p className="text-xs text-text-muted text-center py-4">
                        {committedSearch ? `No courses found for "${committedSearch}"` : "Search for courses to add."}
                      </p>
                    ) : (
                      availableCourses.map((course) => (
                        <div
                          key={course.id}
                          className="flex items-center gap-3 p-3 rounded-lg bg-surface-overlay border border-surface-border hover:border-primary/40 transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-text-primary line-clamp-1">{course.title}</p>
                            <div className="flex gap-1 mt-0.5">
                              <Badge variant="muted">{course.provider}</Badge>
                              <Badge variant={difficultyVariant(course.level)}>{course.level}</Badge>
                            </div>
                          </div>
                          <Button
                            size="sm"
                            isLoading={addingCourseId === course.id}
                            onClick={() => handleAddCourse(course)}
                            className="flex-shrink-0 text-xs"
                          >
                            Add
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                </Card>
              )}
 
              {/* Course list */}
              {courses.length === 0 ? (
                <div className="py-8 text-center border border-dashed border-surface-border rounded-xl">
                  <p className="text-sm text-text-muted mb-3">No courses in this combo yet.</p>
                  {isOwner && (
                    <Button size="sm" variant="secondary" onClick={() => setIsAddCoursesOpen(true)}>
                      Add your first course
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {courses.map((comboCourse, index) => {
                    const courseId = comboCourse.course?.id ?? `course-${index}`;
                    const isCompleted = completedIds.has(courseId);
                    const isRemoving = removingCourseId === courseId;
 
                    return (
                      <Card
                        key={courseId}
                        className={cn(
                          "p-4 flex items-start gap-4 transition-all duration-150",
                          isCompleted ? "border-accent/30 bg-accent-muted/20" : ""
                        )}
                      >
                        {/* Step number / checkmark */}
                        <div className={cn(
                          "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold",
                          isCompleted ? "bg-accent text-white" : "bg-surface-overlay text-text-muted border border-surface-border"
                        )}>
                          {isCompleted ? (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                          ) : index + 1}
                        </div>
 
                        {/* Course info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            {comboCourse.course?.provider && <Badge variant="muted">{comboCourse.course.provider}</Badge>}
                            {!comboCourse.is_required && <Badge variant="muted">Optional</Badge>}
                          </div>
                          {comboCourse.course ? (
                            <Link href={ROUTES.COURSE_DETAIL(comboCourse.course.id)} className="text-sm font-semibold text-text-primary hover:text-primary transition-colors">
                              {comboCourse.course.title}
                            </Link>
                          ) : (
                            <p className="text-sm text-text-muted">Course unavailable</p>
                          )}
                          {comboCourse.course?.short_description && (
                            <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{comboCourse.course.short_description}</p>
                          )}
                        </div>
 
                        {/* Action buttons */}
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          {/* Owner: reorder */}
                          {isOwner && (
                            <div className="flex flex-col gap-0.5">
                              <button
                                type="button"
                                onClick={() => handleMoveCourse(index, "up")}
                                disabled={index === 0}
                                className="p-0.5 text-text-muted hover:text-primary disabled:opacity-30 transition-colors text-xs"
                                aria-label="Move up"
                              >↑</button>
                              <button
                                type="button"
                                onClick={() => handleMoveCourse(index, "down")}
                                disabled={index === courses.length - 1}
                                className="p-0.5 text-text-muted hover:text-primary disabled:opacity-30 transition-colors text-xs"
                                aria-label="Move down"
                              >↓</button>
                            </div>
                          )}
 
                          {/* Complete toggle */}
                          {isAuthenticated && comboCourse.course && (
                            <Button
                              size="sm"
                              variant={isCompleted ? "ghost" : "secondary"}
                              className="text-xs"
                              onClick={() => isCompleted
                                ? startCourse(comboCourse.course.id)
                                : completeCourse(comboCourse.course.id)
                              }
                            >
                              {isCompleted ? "Undo" : "Complete"}
                            </Button>
                          )}
 
                          {/* Owner: remove */}
                          {isOwner && comboCourse.course && (
                            <Button
                              size="sm"
                              variant="danger"
                              isLoading={isRemoving}
                              className="text-xs px-2"
                              title="Remove from combo"
                              onClick={() => handleRemoveCourse(comboCourse.course.id)}
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </Button>
                          )}
                        </div>
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
 
          {/* ─── Right: Sidebar ──────────────────────────────────────── */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 space-y-4">
 
              {/* Progress card */}
              {isAuthenticated && (
                <Card className="p-5">
                  <h3 className="text-sm font-semibold text-text-primary mb-3">Your Progress</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">
                        {progress?.completed_courses ?? 0} of {progress?.total_courses ?? courses.length} complete
                      </span>
                      <span className="font-semibold text-text-primary">{Math.round(completionPct)}%</span>
                    </div>
                    <div className="h-2 bg-surface-overlay rounded-full overflow-hidden">
                      <div className="h-full bg-accent rounded-full transition-all duration-300" style={{ width: `${completionPct}%` }} />
                    </div>
                    {completionPct === 100 && <p className="text-xs text-accent font-medium">Combo complete!</p>}
                  </div>
                </Card>
              )}
 
              {/* Info card */}
              <Card className="p-5 space-y-3">
                <h3 className="text-sm font-semibold text-text-primary">About this path</h3>
                <div className="space-y-2 text-sm text-text-secondary">
                  <div className="flex justify-between">
                    <span>Courses</span>
                    <span className="font-medium text-text-primary">{courses.length}</span>
                  </div>
                  {combo.estimated_weeks > 0 && (
                    <div className="flex justify-between">
                      <span>Duration</span>
                      <span className="font-medium text-text-primary">{combo.estimated_weeks} weeks</span>
                    </div>
                  )}
                  {combo.estimated_hours_per_week > 0 && (
                    <div className="flex justify-between">
                      <span>Per week</span>
                      <span className="font-medium text-text-primary">{combo.estimated_hours_per_week}h</span>
                    </div>
                  )}
                  {(combo.average_rating ?? 0) > 0 && (
                    <div className="flex justify-between">
                      <span>Rating</span>
                      <span className="font-medium text-text-primary">
                        &#11088; {formatRating(combo.average_rating ?? 0)} ({formatRatingCount(combo.rating_count ?? 0)})
                      </span>
                    </div>
                  )}
                </div>
 
                {/* Publish toggle — prominent in sidebar for owner */}
                {isOwner && (
                  <div className="pt-3 border-t border-surface-border">
                    <button
                      type="button"
                      onClick={handleTogglePublic}
                      className={cn(
                        "w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-sm font-medium transition-all duration-150",
                        combo.is_public
                          ? "bg-accent-muted border-accent/30 text-accent hover:bg-accent-muted/80"
                          : "bg-primary-subtle border-primary/30 text-primary hover:bg-primary-muted/30"
                      )}
                    >
                      <span>{combo.is_public ? "Make Private" : "Publish Combo"}</span>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        {combo.is_public
                          ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                          : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        }
                      </svg>
                    </button>
                    {combo.is_public && (
                      <p className="text-xs text-text-muted mt-1.5 text-center">
                        Others can now find and rate this combo.
                      </p>
                    )}
                  </div>
                )}
 
                {/* Save / Unsave */}
                {isAuthenticated ? (
                  <div className={cn("pt-3 border-t border-surface-border", isOwner && "")}>
                    <Button
                      fullWidth
                      size="sm"
                      variant="ghost"
                      isLoading={isSaving || isUnsaving}
                      onClick={() => isSaved ? unsaveCombo(id) : saveCombo(id)}
                    >
                      {isSaved ? (
                        <span className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-primary" fill="currentColor" viewBox="0 0 24 24"><path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>
                          Saved
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>
                          Save this combo
                        </span>
                      )}
                    </Button>
                  </div>
                ) : (
                  <div className="pt-3 border-t border-surface-border">
                    <Link href={ROUTES.LOGIN}><Button fullWidth size="sm">Log in to track progress</Button></Link>
                  </div>
                )}
              </Card>
 
              {/* Tags */}
              {combo.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {combo.tags.map((tag) => (
                    <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-surface-overlay border border-surface-border text-text-muted">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
 
      {/* Delete Confirmation Modal */}
      <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)} title="Delete Combo" size="sm">
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            Are you sure you want to delete{" "}
            <span className="font-semibold text-text-primary">{combo.title}</span>?
            This cannot be undone.
          </p>
          <div className="flex gap-3 justify-end">
            <Button variant="ghost" onClick={() => setShowDeleteModal(false)}>Cancel</Button>
            <Button variant="danger" isLoading={isDeleting} onClick={handleDeleteCombo}>Delete Combo</Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
}
 