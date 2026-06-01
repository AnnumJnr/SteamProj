/**
 * app/dashboard/progress/page.tsx
 * All user progress, grouped by status.
 * Full progress list with unenroll action per course.
 * Unenroll calls DELETE /progress/{course_id}/ — removes all progress for that course.
 */
 
"use client";
 
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useProgress, useProgressSummary, useUnenrollCourse } from "@/hooks/useProgress";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ROUTES } from "@/constants/routes";
import type { ProgressStatus } from "@/types/progress";
 
const STATUS_CONFIG: Record<ProgressStatus, { label: string; variant: "success" | "warning" | "muted" }> = {
  completed:   { label: "Completed",   variant: "success" },
  in_progress: { label: "In Progress", variant: "warning" },
  not_started: { label: "Not Started", variant: "muted"   },
};
 
export default function ProgressPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: progressData, isLoading } = useProgress();
  const { data: summary } = useProgressSummary();
  const { mutate: unenrollCourse, isPending: isUnenrolling } = useUnenrollCourse();
 
  const [confirmCourseId, setConfirmCourseId] = useState<string | null>(null);
  const [confirmCourseTitle, setConfirmCourseTitle] = useState<string>("");
 
  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push(ROUTES.LOGIN);
  }, [authLoading, isAuthenticated, router]);
 
  if (authLoading || !isAuthenticated) return <LoadingState className="py-24" />;
 
  const progress = progressData?.results ?? [];
 
  function handleUnenroll() {
    if (!confirmCourseId) return;
    unenrollCourse(confirmCourseId, {
      onSuccess: () => setConfirmCourseId(null),
    });
  }
 
  return (
    <PageContainer>
      <div className="py-8">
        <div className="mb-8">
          <nav className="text-sm text-text-muted mb-3">
            <Link href={ROUTES.DASHBOARD} className="hover:text-primary transition-colors">Dashboard</Link>
            <span className="mx-2">/</span>
            <span>My Progress</span>
          </nav>
          <h1 className="text-2xl font-bold text-text-primary">My Progress</h1>
        </div>
 
        {/* Summary stats */}
        {summary && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            {(["completed", "in_progress", "not_started"] as ProgressStatus[]).map((status) => (
              <Card key={status} className="p-4 text-center">
                <p className="text-2xl font-bold text-text-primary">{summary[status]}</p>
                <p className="text-xs text-text-muted mt-1">{STATUS_CONFIG[status].label}</p>
              </Card>
            ))}
          </div>
        )}
 
        {isLoading ? (
          <LoadingState message="Loading progress..." />
        ) : progress.length === 0 ? (
          <EmptyState
            title="No progress yet"
            description="Open a course and click Mark as Started to begin tracking."
            action={{ label: "Explore courses", onClick: () => router.push(ROUTES.COURSES) }}
          />
        ) : (
          <div className="space-y-3">
            {progress.map((p) => {
              const config = STATUS_CONFIG[p.status];
              return (
                <Card key={p.id} className="p-4 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={config.variant}>{config.label}</Badge>
                      <Badge variant="muted">{p.course.provider}</Badge>
                    </div>
                    <p className="text-sm font-medium text-text-primary line-clamp-1">
                      {p.course.title}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">{p.course.category}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Link href={ROUTES.COURSE_DETAIL(p.course.id)}>
                      <Button size="sm" variant="secondary">
                        {p.status === "completed" ? "Review" : "Continue"}
                      </Button>
                    </Link>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-danger hover:text-danger"
                      onClick={() => {
                        setConfirmCourseId(p.course.id);
                        setConfirmCourseTitle(p.course.title);
                      }}
                    >
                      Unenroll
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
 
      {/* Unenroll confirmation modal */}
      <Modal
        isOpen={Boolean(confirmCourseId)}
        onClose={() => setConfirmCourseId(null)}
        title="Unenroll from course"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            Are you sure you want to unenroll from{" "}
            <span className="font-semibold text-text-primary">{confirmCourseTitle}</span>?
            All your progress for this course will be permanently deleted.
          </p>
          <div className="flex gap-3 justify-end">
            <Button variant="ghost" onClick={() => setConfirmCourseId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              isLoading={isUnenrolling}
              onClick={handleUnenroll}
            >
              Unenroll
            </Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
}
 