/**
 * app/dashboard/saved/page.tsx
 * All saved courses and combos for the authenticated user.
 * Fix: unsaveCourse and unsaveCombo now pass the course/combo ID directly,
 * not the saved-item record id.
 * Source: apps/progress/urls.py → saved/courses/<uuid:course_id>/
 *                                  saved/combos/<uuid:combo_id>/
 */
 
"use client";
 
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useSavedCourses, useSavedCombos, useUnsaveCourse, useUnsaveCombo } from "@/hooks/useSavedItems";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ROUTES } from "@/constants/routes";
import { cn } from "@/lib/utils";
 
type Tab = "courses" | "combos";
 
export default function SavedPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("courses");
 
  const { data: savedCourses, isLoading: coursesLoading } = useSavedCourses();
  const { data: savedCombos, isLoading: combosLoading } = useSavedCombos();
  const { mutate: unsaveCourse, isPending: isUnsavingCourse } = useUnsaveCourse();
  const { mutate: unsaveCombo, isPending: isUnsavingCombo } = useUnsaveCombo();
 
  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push(ROUTES.LOGIN);
  }, [authLoading, isAuthenticated, router]);
 
  if (authLoading || !isAuthenticated) return <LoadingState className="py-24" />;
 
  const courses = savedCourses?.results ?? [];
  const combos = savedCombos?.results ?? [];
 
  return (
    <PageContainer>
      <div className="py-8">
        <div className="mb-6">
          <nav className="text-sm text-text-muted mb-3">
            <Link href={ROUTES.DASHBOARD} className="hover:text-primary transition-colors">Dashboard</Link>
            <span className="mx-2">/</span>
            <span>Saved Items</span>
          </nav>
          <h1 className="text-2xl font-bold text-text-primary">Saved Items</h1>
        </div>
 
        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-surface-border">
          {(["courses", "combos"] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px",
                activeTab === tab
                  ? "border-primary text-primary"
                  : "border-transparent text-text-muted hover:text-text-secondary"
              )}
            >
              {tab} ({tab === "courses" ? (savedCourses?.count ?? 0) : (savedCombos?.count ?? 0)})
            </button>
          ))}
        </div>
 
        {/* Courses tab */}
        {activeTab === "courses" && (
          coursesLoading ? <LoadingState /> :
          courses.length === 0 ? (
            <EmptyState
              title="No saved courses"
              description="Save courses to revisit them later."
              action={{ label: "Browse courses", onClick: () => router.push(ROUTES.COURSES) }}
            />
          ) : (
            <div className="space-y-3">
              {courses.map((saved) => (
                <Card key={saved.id} className="p-4 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="muted">{saved.course.provider}</Badge>
                      <Badge variant={
                        saved.course.level === "Beginner" ? "success" :
                        saved.course.level === "Intermediate" ? "warning" : "danger"
                      }>
                        {saved.course.level}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium text-text-primary line-clamp-1">
                      {saved.course.title}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">{saved.course.category}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Link href={ROUTES.COURSE_DETAIL(saved.course.id)}>
                      <Button size="sm" variant="secondary">View</Button>
                    </Link>
                    {/* Pass course.id directly — backend URL: /saved/courses/{course_id}/ */}
                    <Button
                      size="sm"
                      variant="ghost"
                      isLoading={isUnsavingCourse}
                      onClick={() => unsaveCourse(saved.course.id)}
                      className="text-danger hover:text-danger"
                    >
                      Remove
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )
        )}
 
        {/* Combos tab */}
        {activeTab === "combos" && (
          combosLoading ? <LoadingState /> :
          combos.length === 0 ? (
            <EmptyState
              title="No saved combos"
              description="Save combo paths you want to follow later."
              action={{ label: "Browse combos", onClick: () => router.push(ROUTES.COMBOS) }}
            />
          ) : (
            <div className="space-y-3">
              {combos.map((saved) => (
                <Card key={saved.id} className="p-4 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="muted">{saved.combo.difficulty}</Badge>
                      <Badge variant="muted">{saved.combo.course_count} courses</Badge>
                    </div>
                    <p className="text-sm font-medium text-text-primary line-clamp-1">
                      {saved.combo.title}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">{saved.combo.category}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Link href={ROUTES.COMBO_DETAIL(saved.combo.id)}>
                      <Button size="sm" variant="secondary">View</Button>
                    </Link>
                    {/* Pass combo.id directly — backend URL: /saved/combos/{combo_id}/ */}
                    <Button
                      size="sm"
                      variant="ghost"
                      isLoading={isUnsavingCombo}
                      onClick={() => unsaveCombo(saved.combo.id)}
                      className="text-danger hover:text-danger"
                    >
                      Remove
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )
        )}
      </div>
    </PageContainer>
  );
}
 