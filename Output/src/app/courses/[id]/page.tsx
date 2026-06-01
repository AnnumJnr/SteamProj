/**
 * app/courses/[id]/page.tsx
 * Course detail page. Shows full course info + embedded YouTube player (with fallback).
 *
 * YouTube embed strategy (per master reference §3):
 *   DEFAULT:  Embed via <iframe> using the YouTube embed URL
 *   FALLBACK: If embed fails or provider is not YouTube, redirect link to source_url in new tab
 *             FALLBACK comment below marks this location per Rule 2.
 *
 * Analytics: COURSE_VIEWED is fired on mount (OWNER: frontend, per constants/events.ts)
 *
 * Actions available:
 * - Open on provider (always visible)
 * - Mark as Started / Mark as Complete (authenticated)
 * - Unenroll — DELETE /progress/{course_id}/ — removes all progress
 * - Save / Unsave — DELETE /progress/saved/courses/{course_id}/ using COURSE id
 */
 
"use client";
 
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useCourse } from "@/hooks/useCourses";
import { useCompleteCourse, useStartCourse, useUnenrollCourse } from "@/hooks/useProgress";
import { useSaveCourse, useSavedCourses, useUnsaveCourse } from "@/hooks/useSavedItems";
import { useAuth } from "@/hooks/useAuth";
import { PageContainer } from "@/components/layout/PageContainer";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { ROUTES } from "@/constants/routes";
import { formatDuration, formatRating, formatRatingCount, extractYouTubeId } from "@/lib/utils";
 
export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated } = useAuth();
  const { data: course, isLoading, isError, refetch } = useCourse(id);
  const { mutate: startCourse, isPending: isStarting } = useStartCourse();
  const { mutate: completeCourse, isPending: isCompleting } = useCompleteCourse();
  const { mutate: unenrollCourse, isPending: isUnenrolling } = useUnenrollCourse();
  const { mutate: saveCourse, isPending: isSaving } = useSaveCourse();
  const { mutate: unsaveCourse, isPending: isUnsaving } = useUnsaveCourse();
  const { data: savedCoursesData } = useSavedCourses();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
 
  // Check saved status using course id directly
  const isSaved = savedCoursesData?.results?.some((s) => s.course.id === id) ?? false;
 
  useEffect(() => {
    if (!course) return;
    if (typeof window !== "undefined" && (window as unknown as { posthog?: { capture: (e: string, p: Record<string, unknown>) => void } }).posthog) {
      (window as unknown as { posthog: { capture: (e: string, p: Record<string, unknown>) => void } }).posthog.capture("course_viewed", {
        course_id: course.id, course_title: course.title, provider: course.provider,
      });
    }
  }, [course]);
 
  function showMessage(msg: string) {
    setActionMessage(msg);
    setTimeout(() => setActionMessage(null), 3000);
  }
 
  if (isLoading) return <LoadingState message="Loading course..." className="py-24" />;
  if (isError || !course) {
    return <PageContainer><ErrorState title="Course not found" onRetry={() => refetch()} /></PageContainer>;
  }
 
  const youtubeId = course.provider === "YouTube" ? extractYouTubeId(course.source_url) : null;
  const levelVariant = course.level === "Beginner" ? "success" : course.level === "Intermediate" ? "warning" : "danger" as "success" | "warning" | "danger";
 
  return (
    <PageContainer>
      <div className="py-8">
        <nav className="flex items-center gap-2 text-sm text-text-muted mb-6">
          <Link href={ROUTES.COURSES} className="hover:text-primary transition-colors">Courses</Link>
          <span>/</span>
          <span className="text-text-secondary truncate max-w-xs">{course.title}</span>
        </nav>
 
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
 
            {/* Video / thumbnail */}
            <div className="rounded-xl overflow-hidden bg-surface-overlay aspect-video w-full">
              {youtubeId ? (
                // DEFAULT: YouTube iframe embed
                // FALLBACK: "Open on YouTube" button in action card
                // CONDITION: Embed blocked by network/browser
                // ACTION: Opens source_url in new tab
                <iframe
                  src={`https://www.youtube.com/embed/${youtubeId}`}
                  title={course.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="w-full h-full border-0"
                />
              ) : course.thumbnail_url ? (
                <div className="relative w-full h-full">
                  <Image src={course.thumbnail_url} alt={course.title} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 66vw" unoptimized />
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-surface-raised">
                  <svg className="w-16 h-16 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
            </div>
 
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-3">
                <Badge variant="primary">{course.provider}</Badge>
                <Badge variant={levelVariant}>{course.level}</Badge>
                <Badge variant="muted">{course.format}</Badge>
                {course.is_free && <Badge variant="success">Free</Badge>}
              </div>
              <h1 className="text-2xl font-bold text-text-primary leading-snug">{course.title}</h1>
              {course.instructor && <p className="text-sm text-text-muted mt-1">by {course.instructor}</p>}
            </div>
 
            <div>
              <h2 className="text-base font-semibold text-text-primary mb-2">About this course</h2>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
                {course.full_description || course.short_description}
              </p>
            </div>
 
            {course.learning_outcomes?.length > 0 && (
              <div>
                <h2 className="text-base font-semibold text-text-primary mb-3">What you will learn</h2>
                <ul className="space-y-2">
                  {course.learning_outcomes.map((outcome, i) => (
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
 
            {course.prerequisites?.length > 0 && (
              <div>
                <h2 className="text-base font-semibold text-text-primary mb-3">Prerequisites</h2>
                <ul className="space-y-2">
                  {course.prerequisites.map((prereq, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-text-secondary">
                      <svg className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {prereq}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
 
          {/* Action card */}
          <div className="lg:col-span-1">
            <div className="sticky top-24">
              <Card className="p-6 space-y-4">
                {course.rating_average > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <svg key={star} className={`w-4 h-4 ${star <= Math.round(course.rating_average) ? "text-warning" : "text-surface-border"}`} fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                    <span className="text-sm font-semibold text-text-primary">{formatRating(course.rating_average)}</span>
                    <span className="text-sm text-text-muted">({formatRatingCount(course.rating_count)})</span>
                  </div>
                )}
 
                <div className="space-y-2 text-sm">
                  {(course.duration_hours > 0 || course.duration_minutes > 0) && (
                    <div className="flex items-center gap-2 text-text-secondary">
                      <svg className="w-4 h-4 text-text-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {formatDuration(course.duration_hours, course.duration_minutes)}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-text-secondary">
                    <svg className="w-4 h-4 text-text-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    {course.age_group}
                  </div>
                </div>
 
                {/* Action feedback */}
                {actionMessage && (
                  <div className="px-3 py-2 rounded-lg bg-primary-subtle border border-primary/20 text-xs text-primary text-center">
                    {actionMessage}
                  </div>
                )}
 
                <div className="space-y-2 pt-2 border-t border-surface-border">
                  {/* FALLBACK: Open on provider link is the fallback when YouTube embed is blocked */}
                  <a href={course.source_url} target="_blank" rel="noopener noreferrer" className="block">
                    <Button fullWidth variant="primary">Open on {course.provider} &#8599;</Button>
                  </a>
 
                  {isAuthenticated ? (
                    <>
                      <Button fullWidth variant="secondary" isLoading={isStarting}
                        onClick={() => startCourse(id, { onSuccess: () => showMessage("Course marked as started") })}>
                        Mark as Started
                      </Button>
 
                      <Button fullWidth variant="secondary" isLoading={isCompleting}
                        onClick={() => completeCourse(id, { onSuccess: () => showMessage("Course marked as complete") })}>
                        Mark as Complete
                      </Button>
 
                      {/* Save / Unsave — passes course ID directly */}
                      <Button fullWidth variant="ghost" isLoading={isSaving || isUnsaving}
                        onClick={() => isSaved
                          ? unsaveCourse(id, { onSuccess: () => showMessage("Removed from saved items") })
                          : saveCourse(id, { onSuccess: () => showMessage("Saved to your library") })
                        }>
                        {isSaved ? (
                          <span className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-primary" fill="currentColor" viewBox="0 0 24 24"><path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>
                            Saved
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>
                            Save this course
                          </span>
                        )}
                      </Button>
 
                      {/* Unenroll — removes all progress for this course */}
                      <Button fullWidth variant="ghost" isLoading={isUnenrolling}
                        onClick={() => unenrollCourse(id, { onSuccess: () => showMessage("Unenrolled from course") })}
                        className="text-danger hover:text-danger border border-transparent hover:border-danger/30">
                        Unenroll from course
                      </Button>
                    </>
                  ) : (
                    <Link href={ROUTES.LOGIN}>
                      <Button fullWidth variant="secondary">Log in to track progress</Button>
                    </Link>
                  )}
                </div>
 
                {course.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-2 border-t border-surface-border">
                    {course.tags.map((tag) => (
                      <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-surface-overlay border border-surface-border text-text-muted">{tag}</span>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
 