/**
 * app/courses/[id]/page.tsx
 * Course detail page. Shows full course info + embedded YouTube player (with fallback).
 *
 * Video gate (matches backend apps/courses → VideoGateMixin):
 *   LOCKED:    Server sends blank source_url, empty videos, video_access_granted=false
 *              → cover art + lock overlay; starting the course unlocks it.
 *   UNLOCKED:  Server sends the stored playlist items → lesson sidebar +
 *              per-video embed. Anonymous users see a "Log in to start" CTA.
 *
 *   FALLBACK: If embed fails or provider is not YouTube, redirect link to source_url in new tab
 *             (source_url only exists post-unlock — see handleStartCourse + useStartCourse invalidation).
 *
 * Analytics: COURSE_VIEWED is fired on mount (OWNER: frontend, per constants/events.ts)
 *
 * Actions available:
 * - Open on provider (only when unlocked)
 * - Mark as Started / Mark as Complete (authenticated)
 * - Unenroll — DELETE /progress/{course_id}/ — removes all progress (re-locks the gate)
 * - Save / Unsave — DELETE /progress/saved/courses/{course_id}/ using COURSE id
 */
 
"use client";
 
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useCourse } from "@/hooks/useCourses";
import { useCompleteCourse, useCourseProgress, useStartCourse, useUnenrollCourse } from "@/hooks/useProgress";
import { useSaveCourse, useSavedCourses, useUnsaveCourse } from "@/hooks/useSavedItems";
import { useAuth } from "@/hooks/useAuth";
import { PageContainer } from "@/components/layout/PageContainer";
import { Badge } from "@/components/ui/Badge";
import { VideoPlaylist } from "@/components/course/VideoPlaylist";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { ROUTES } from "@/constants/routes";
import { formatDuration, formatRating, formatRatingCount, extractYouTubeEmbed } from "@/lib/utils";
 
export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated } = useAuth();
  const { data: course, isLoading, isError, refetch } = useCourse(id);
  const { data: courseProgress } = useCourseProgress(id, isAuthenticated);
  const { mutate: startCourse, isPending: isStarting } = useStartCourse();
  const { mutate: completeCourse, isPending: isCompleting } = useCompleteCourse();
  const { mutate: unenrollCourse, isPending: isUnenrolling } = useUnenrollCourse();
  const { mutate: saveCourse, isPending: isSaving } = useSaveCourse();
  const { mutate: unsaveCourse, isPending: isUnsaving } = useUnsaveCourse();
  const { data: savedCoursesData } = useSavedCourses(isAuthenticated);
  const [showUnenrollModal, setShowUnenrollModal] = useState(false);
  const [hasStartedLocally, setHasStartedLocally] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);

  // Check saved status using course id directly
  const isSaved = savedCoursesData?.results?.some((s) => s.course.id === id) ?? false;
  const hasActiveProgress = Boolean(courseProgress);
  const hasStarted = hasActiveProgress || hasStartedLocally;
  const isCompleted = courseProgress?.status === "completed";

  useEffect(() => {
    setHasStartedLocally(Boolean(courseProgress));
  }, [courseProgress]);
 
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

  // ─── Video gate ───────────────────────────────────────────────────────────
  // The API only serves embed data (source_url / videos) once the user has
  // started the course. Everything below derives from what the server sent:
  // a locked response carries a blank source_url and no videos.
  const isYouTube = course.provider === "YouTube";
  const unlocked = course.video_access_granted;
  const youtubeEmbed = isYouTube && unlocked
    ? extractYouTubeEmbed(course.source_url)
    : null;
  const playlistVideos = isYouTube ? course.videos : [];

  // Active video: the user's pick, falling back to the first lesson
  const activeVideoId =
    selectedVideoId && playlistVideos.some((v) => v.video_id === selectedVideoId)
      ? selectedVideoId
      : playlistVideos[0]?.video_id ?? null;
  const activeVideo = playlistVideos.find((v) => v.video_id === activeVideoId) ?? null;

  // youtubeEmbedSrc — what to mount in the iframe (null → locked/fallback art)
  // PRIORITY 1: Stored playlist lesson (videos served by the API)
  // PRIORITY 2: Coarse playlist embed via source_url (items not ingested yet)
  // PRIORITY 3: null → locked overlay for YouTube, thumbnail otherwise
  const youtubeEmbedSrc = isYouTube
    ? activeVideoId
      ? youtubeEmbed?.type === "playlist"
        ? `https://www.youtube.com/embed/videoseries?list=${youtubeEmbed.id}&index=${(activeVideo?.position ?? 0) + 1}`
        : `https://www.youtube.com/embed/${activeVideoId}`
      : youtubeEmbed
        ? `https://www.youtube.com/embed/${youtubeEmbed.type === "playlist" ? `videoseries?list=${youtubeEmbed.id}` : youtubeEmbed.id}`
        : null
    : null;

  const locked = isYouTube && !unlocked;

  const levelVariant = course.level === "Beginner" ? "success" : course.level === "Intermediate" ? "warning" : "danger" as "success" | "warning" | "danger";

  const handleStartCourse = () => {
    startCourse(id, {
      onSuccess: () => {
        setHasStartedLocally(true);
        showMessage("Course started — lessons unlocked");
        // The course payload unlocks server-side; hook invalidation refetches it
      },
      onError: () => showMessage("Could not start this course. Please try again."),
    });
  };
 
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
              {youtubeEmbedSrc ? (
                // DEFAULT: YouTube iframe embed — the selected playlist lesson
                // (or playlist player for courses whose items aren't ingested yet)
                // FALLBACK: "Open on YouTube" button in action card (post-start)
                // CONDITION: Embed blocked by network/browser
                // ACTION: Opens source_url in new tab
                <iframe
                  key={youtubeEmbedSrc}
                  src={youtubeEmbedSrc}
                  title={course.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="w-full h-full border-0"
                />
              ) : locked ? (
                // GATE: Locked — the course hasn't been started, so the embed
                // is unavailable. Show cover art + the unlock action.
                <div className="relative w-full h-full">
                  {course.thumbnail_url ? (
                    <Image src={course.thumbnail_url} alt={course.title} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 66vw" unoptimized />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-surface-raised">
                      <svg className="w-16 h-16 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-surface-base/85 backdrop-blur-sm flex flex-col items-center justify-center gap-3 p-6 text-center">
                    <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                      <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-text-primary">Start this course to watch</p>
                      <p className="text-xs text-text-secondary mt-1">All lessons and the playlist unlock once you begin.</p>
                    </div>
                    {isAuthenticated ? (
                      <Button variant="primary" isLoading={isStarting} onClick={handleStartCourse}>
                        Start course
                      </Button>
                    ) : (
                      <Link href={ROUTES.LOGIN}>
                        <Button variant="primary">Log in to start</Button>
                      </Link>
                    )}
                  </div>
                </div>
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

            {/* Playlist sidebar — only for unlocked playlist courses */}
            <VideoPlaylist
              videos={playlistVideos}
              activeId={activeVideoId}
              onSelect={(videoId) => setSelectedVideoId(videoId)}
            />

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
                  {isAuthenticated ? (
                    <>
                      {hasStarted ? (
                        <a href={course.source_url} target="_blank" rel="noopener noreferrer" className="block">
                          <Button fullWidth variant="primary">Visit course &#8599;</Button>
                        </a>
                      ) : (
                        <Button fullWidth variant="secondary" isLoading={isStarting}
                          onClick={() => startCourse(id, {
                            onSuccess: () => {
                              setHasStartedLocally(true);
                              showMessage("Course started");
                            },
                            onError: () => showMessage("Could not start this course. Please try again."),
                          })}>
                          Start course
                        </Button>
                      )}

                      {hasStarted && (
                        <Button fullWidth variant={isCompleted ? "ghost" : "secondary"}
                          disabled={isCompleted}
                          isLoading={isCompleting}
                          onClick={() => completeCourse(id, {
                            onSuccess: () => showMessage("Course marked as complete"),
                            onError: () => showMessage("Could not complete this course. Please try again."),
                          })}>
                          {isCompleted ? "Completed" : "Mark as Complete"}
                        </Button>
                      )}
 
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
 
                      {hasActiveProgress && (
                        <Button fullWidth variant="ghost"
                          onClick={() => setShowUnenrollModal(true)}
                          className="text-danger hover:text-danger border border-transparent hover:border-danger/30">
                          Unenroll from course
                        </Button>
                      )}
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

      <Modal
        isOpen={showUnenrollModal}
        onClose={() => setShowUnenrollModal(false)}
        title="Unenroll from course"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            This will pause the course and remove it from your active progress. Your learning history will be preserved.
          </p>
          <div className="flex gap-3 justify-end">
            <Button variant="ghost" onClick={() => setShowUnenrollModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              isLoading={isUnenrolling}
              onClick={() => unenrollCourse(id, {
                onSuccess: () => {
                  setHasStartedLocally(false);
                  setShowUnenrollModal(false);
                  showMessage("Course paused");
                },
              })}
            >
              Unenroll
            </Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
}
 