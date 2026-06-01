/**
 * app/combos/create/page.tsx
 * Custom Combo builder. Protected route — requires authentication.
 * Allows users to create a private combo from available courses.
 *
 * MVP scope: Title, description, difficulty, and course selection.
 * Search fix: course search now calls the backend with the search param
 * instead of filtering client-side from a single page of 20 results.
 * This means typing in the search box queries /api/v1/courses/?search=...
 * and shows all matching courses, not just matches within the first 20.
 *
 * FormEvent: React.FormEvent is NOT deprecated. The TypeScript warning
 * visible in some editors is about the browser's native FormDataEvent,
 * not React's FormEvent. It is safe to use and has no runtime effect.
 */
 
"use client";
 
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useCreateCombo } from "@/hooks/useCombos";
import { useCourses } from "@/hooks/useCourses";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ROUTES } from "@/constants/routes";
import { STEM_CATEGORIES, COMBO_DIFFICULTIES } from "@/constants/filters";
import type { CreateComboPayload } from "@/types/combo";
import type { Course } from "@/types/course";
 
interface SelectedCourse {
  course: Course;
  order: number;
  is_required: boolean;
  note: string;
}
 
export default function CreateComboPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { mutate: createCombo, isPending } = useCreateCombo();
 
  const [title, setTitle] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [selectedCourses, setSelectedCourses] = useState<SelectedCourse[]>([]);
 
  // Search is sent to the backend — not filtered client-side
  // This means all matching courses are returned, not just matches within page 1
  const [courseSearch, setCourseSearch] = useState("");
  const [searchQuery, setSearchQuery] = useState(""); // committed search term
 
  const { data: coursesData, isLoading: coursesLoading } = useCourses({
    search: searchQuery || undefined,
    page: 1,
  });
 
  const [error, setError] = useState<string | null>(null);
 
  if (!isAuthenticated) {
    return (
      <PageContainer narrow>
        <div className="py-24 text-center">
          <h1 className="text-xl font-bold text-text-primary mb-3">Sign in to create a Combo</h1>
          <p className="text-sm text-text-secondary mb-6">
            You need an account to build and save custom learning paths.
          </p>
          <Link href={ROUTES.LOGIN}><Button>Log in</Button></Link>
        </div>
      </PageContainer>
    );
  }
 
  // Available = all returned courses minus already selected ones
  const availableCourses = (coursesData?.results ?? []).filter(
    (c) => !selectedCourses.find((s) => s.course.id === c.id)
  );
 
  function addCourse(course: Course) {
    setSelectedCourses((prev) => [
      ...prev,
      { course, order: prev.length + 1, is_required: true, note: "" },
    ]);
  }
 
  function removeCourse(courseId: string) {
    setSelectedCourses((prev) =>
      prev
        .filter((s) => s.course.id !== courseId)
        .map((s, i) => ({ ...s, order: i + 1 }))
    );
  }
 
  function moveCourse(index: number, direction: "up" | "down") {
    setSelectedCourses((prev) => {
      const next = [...prev];
      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= next.length) return prev;
      [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
      return next.map((s, i) => ({ ...s, order: i + 1 }));
    });
  }
 
  function handleSearchCommit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSearchQuery(courseSearch.trim());
  }
 
  function handleSubmit() {
    setError(null);
 
    if (!title.trim())            { setError("Title is required.");                    return; }
    if (!shortDescription.trim()) { setError("Description is required.");              return; }
    if (!category)                { setError("Please select a subject category.");     return; }
    if (!difficulty)              { setError("Please select a difficulty level.");     return; }
    if (selectedCourses.length < 2) { setError("A combo needs at least 2 courses."); return; }
 
    const payload: CreateComboPayload = {
      title: title.trim(),
      short_description: shortDescription.trim(),
      category,
      difficulty,
      is_public: false,
      courses: selectedCourses.map((s) => ({
        course_id: s.course.id,
        order: s.order,
        is_required: s.is_required,
        note: s.note || undefined,
      })),
    };
 
    createCombo(payload, {
      onSuccess: (combo) => router.push(ROUTES.COMBO_DETAIL(combo.id)),
      onError: (err: unknown) => {
        setError(
          (err as { detail?: string })?.detail || "Failed to create combo. Please try again."
        );
      },
    });
  }
 
  return (
    <PageContainer>
      <div className="py-8 max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text-primary mb-1">Create a Combo Path</h1>
          <p className="text-sm text-text-secondary">
            Build a structured learning sequence from available courses. Private by default.
          </p>
        </div>
 
        {error && (
          <div className="mb-6 px-4 py-3 rounded-lg bg-danger/10 border border-danger/30 text-sm text-danger">
            {error}
          </div>
        )}
 
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
 
          {/* ─── Left: Combo details ─────────────────────────────────── */}
          <div className="space-y-5">
            <h2 className="text-base font-semibold text-text-primary">Combo details</h2>
 
            <Input
              label="Title"
              placeholder="e.g. Full Stack Web Development"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
 
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-primary">Description</label>
              <textarea
                placeholder="What will learners gain from this combo path?"
                value={shortDescription}
                onChange={(e) => setShortDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors resize-none"
              />
            </div>
 
            {/* Category */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-primary">Subject category</label>
              <div className="grid grid-cols-2 gap-2">
                {STEM_CATEGORIES.map((cat) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => setCategory(cat.value)}
                    className={`px-3 py-2 rounded-lg text-sm text-left transition-all ${
                      category === cat.value
                        ? "bg-primary-subtle border border-primary/40 text-primary font-medium"
                        : "bg-surface-overlay border border-surface-border text-text-secondary hover:border-primary/30"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>
 
            {/* Difficulty */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-primary">Difficulty</label>
              <div className="flex gap-2">
                {COMBO_DIFFICULTIES.map((d) => (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => setDifficulty(d.value)}
                    className={`flex-1 py-2 rounded-lg text-sm transition-all ${
                      difficulty === d.value
                        ? "bg-primary-subtle border border-primary/40 text-primary font-medium"
                        : "bg-surface-overlay border border-surface-border text-text-secondary hover:border-primary/30"
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
 
            {/* Selected courses — ordered list */}
            <div>
              <h3 className="text-sm font-medium text-text-primary mb-2">
                Selected courses ({selectedCourses.length})
              </h3>
              {selectedCourses.length === 0 ? (
                <p className="text-xs text-text-muted italic py-4 text-center border border-dashed border-surface-border rounded-lg">
                  Add courses from the right panel
                </p>
              ) : (
                <div className="space-y-2">
                  {selectedCourses.map((sc, index) => (
                    <Card key={sc.course.id} className="p-3 flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-surface-overlay border border-surface-border text-xs flex items-center justify-center text-text-muted font-medium flex-shrink-0">
                        {sc.order}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-text-primary line-clamp-1">{sc.course.title}</p>
                        <Badge variant="muted">{sc.course.provider}</Badge>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button
                          type="button"
                          onClick={() => moveCourse(index, "up")}
                          disabled={index === 0}
                          className="p-1 text-text-muted hover:text-primary disabled:opacity-30 transition-colors"
                          aria-label="Move up"
                        >↑</button>
                        <button
                          type="button"
                          onClick={() => moveCourse(index, "down")}
                          disabled={index === selectedCourses.length - 1}
                          className="p-1 text-text-muted hover:text-primary disabled:opacity-30 transition-colors"
                          aria-label="Move down"
                        >↓</button>
                        <button
                          type="button"
                          onClick={() => removeCourse(sc.course.id)}
                          className="p-1 text-text-muted hover:text-danger transition-colors"
                          aria-label="Remove course"
                        >✕</button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
 
            <Button fullWidth onClick={handleSubmit} isLoading={isPending}>
              Create Combo Path
            </Button>
          </div>
 
          {/* ─── Right: Course picker with backend search ─────────────── */}
          <div>
            <h2 className="text-base font-semibold text-text-primary mb-4">Add courses</h2>
 
            {/* Search form — submits to backend on Enter or click */}
            <form onSubmit={handleSearchCommit} className="relative mb-3">
              <input
                type="search"
                placeholder="Search all courses by title or category..."
                value={courseSearch}
                onChange={(e) => setCourseSearch(e.target.value)}
                className="w-full px-3 py-2 pr-16 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs bg-primary text-white rounded-md hover:bg-primary-hover transition-colors"
              >
                Search
              </button>
            </form>
 
            {/* Clear search */}
            {searchQuery && (
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-text-muted">
                  Results for &ldquo;{searchQuery}&rdquo; — {coursesData?.count ?? 0} found
                </p>
                <button
                  type="button"
                  onClick={() => { setSearchQuery(""); setCourseSearch(""); }}
                  className="text-xs text-primary hover:text-primary-hover"
                >
                  Clear
                </button>
              </div>
            )}
 
            {/* Course list */}
            <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
              {coursesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : availableCourses.length === 0 ? (
                <p className="text-sm text-text-muted text-center py-8">
                  {searchQuery
                    ? `No courses found for "${searchQuery}"`
                    : "No courses available to add."}
                </p>
              ) : (
                availableCourses.map((course) => (
                  <Card
                    key={course.id}
                    className="p-3 flex items-center gap-3 cursor-pointer hover:border-primary transition-all duration-150"
                    onClick={() => addCourse(course)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-text-primary line-clamp-1">{course.title}</p>
                      <div className="flex gap-1 mt-1">
                        <Badge variant="muted">{course.provider}</Badge>
                        <Badge variant={
                          course.level === "Beginner" ? "success" :
                          course.level === "Intermediate" ? "warning" : "danger"
                        }>
                          {course.level}
                        </Badge>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="w-7 h-7 rounded-full bg-primary/10 text-primary hover:bg-primary hover:text-white flex items-center justify-center flex-shrink-0 transition-colors text-sm font-bold"
                    >
                      +
                    </button>
                  </Card>
                ))
              )}
 
              {/* Pagination note */}
              {(coursesData?.count ?? 0) > (coursesData?.results?.length ?? 0) && !searchQuery && (
                <p className="text-xs text-text-muted text-center py-2">
                  Showing first 20 courses. Use search to find specific courses.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
 