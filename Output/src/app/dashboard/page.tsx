/**
 * app/dashboard/page.tsx
 * User dashboard — overview of progress, saved items, and active combos.
 * Protected route: redirects to login if not authenticated.
 *  Enrolled count = in_progress + completed (started OR finished = enrolled).
 * A course becomes enrolled the moment the user clicks "Mark as Started".
 * User dashboard — corrected to use average_rating (not rating_average)
 * and created_by_type (not created_by) from backend serializer.
 */
 
"use client";
 
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useProgressSummary, useProgress } from "@/hooks/useProgress";
import { useSavedCourses, useSavedCombos } from "@/hooks/useSavedItems";
import { useMyCombos } from "@/hooks/useCombos";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import { LoadingState } from "@/components/shared/LoadingState";
import { ROUTES } from "@/constants/routes";
 
interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  colour: string;
}
 
function StatCard({ label, value, icon, colour }: StatCardProps) {
  return (
    <Card className="p-5 flex items-center gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${colour}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-text-primary">{value}</p>
        <p className="text-xs text-text-muted">{label}</p>
      </div>
    </Card>
  );
}
 
export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: summary } = useProgressSummary();
  const { data: progressData } = useProgress();
  const { data: savedCourses } = useSavedCourses();
  const { data: savedCombos } = useSavedCombos();
  const { data: myCombos } = useMyCombos();
 
  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push(ROUTES.LOGIN);
  }, [authLoading, isAuthenticated, router]);
 
  if (authLoading || !isAuthenticated) return <LoadingState className="py-24" />;
 
  // Enrolled = in_progress + completed
  const enrolledCount = (summary?.in_progress ?? 0) + (summary?.completed ?? 0);
 
  const inProgressCourses = progressData?.results?.filter(
    (p) => p.status === "in_progress"
  ) ?? [];
 
  const displayName = user?.profile?.display_name || user?.email?.split("@")[0] || "Learner";
 
  return (
    <PageContainer>
      <div className="py-8 space-y-10">
 
        {/* Welcome header */}
        <div className="flex items-center gap-4">
          <Avatar
            src={user?.profile?.avatar_url}
            name={user?.profile?.display_name}
            email={user?.email ?? ""}
            size="lg"
          />
          <div>
            <h1 className="text-2xl font-bold text-text-primary">
              Welcome back, {displayName} 👋
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">Keep learning, keep growing!</p>
          </div>
        </div>
 
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Courses Enrolled" value={enrolledCount}
            colour="bg-blue-900/30 text-blue-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>}
          />
          <StatCard label="Completed" value={summary?.completed ?? 0}
            colour="bg-green-900/30 text-green-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard label="In Progress" value={summary?.in_progress ?? 0}
            colour="bg-primary-subtle text-primary"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          />
          <StatCard label="Saved Items" value={(savedCourses?.count ?? 0) + (savedCombos?.count ?? 0)}
            colour="bg-yellow-900/30 text-yellow-400"
            icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>}
          />
        </div>
 
        {/* Continue Learning */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">Continue Learning</h2>
            <Link href={ROUTES.DASHBOARD_PROGRESS}>
              <Button variant="ghost" size="sm">View all →</Button>
            </Link>
          </div>
 
          {inProgressCourses.length === 0 ? (
            <Card className="p-6 text-center">
              <p className="text-sm text-text-muted mb-3">
                No courses in progress yet. Open a course and click &ldquo;Mark as Started&rdquo; to enrol.
              </p>
              <Link href={ROUTES.COURSES}><Button size="sm">Explore courses</Button></Link>
            </Card>
          ) : (
            <div className="space-y-3">
              {inProgressCourses.slice(0, 4).map((p) => (
                <Card key={p.id} className="p-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-primary-subtle flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary line-clamp-1">{p.course.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="muted">{p.course.provider}</Badge>
                      <span className="text-xs text-text-muted">{p.course.category}</span>
                    </div>
                  </div>
                  <Link href={ROUTES.COURSE_DETAIL(p.course.id)} className="flex-shrink-0">
                    <Button size="sm" variant="secondary">Continue</Button>
                  </Link>
                </Card>
              ))}
            </div>
          )}
        </div>
 
        {/* My Combos */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">My Combo Paths</h2>
            <Link href={ROUTES.COMBO_CREATE}>
              <Button variant="secondary" size="sm">+ Create Combo</Button>
            </Link>
          </div>
 
          {(myCombos?.results?.length ?? 0) === 0 ? (
            <Card className="p-6 text-center">
              <p className="text-sm text-text-muted mb-3">You haven&apos;t created any combos yet.</p>
              <Link href={ROUTES.COMBO_CREATE}><Button size="sm">Build your first combo</Button></Link>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {myCombos?.results?.slice(0, 3).map((combo) => (
                <Link key={combo.id} href={ROUTES.COMBO_DETAIL(combo.id)}>
                  <Card variant="interactive" className="p-4 h-full">
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="muted">{combo.difficulty}</Badge>
                      {combo.is_public
                        ? <Badge variant="success">Public</Badge>
                        : <Badge variant="muted">Private</Badge>
                      }
                    </div>
                    <p className="text-sm font-semibold text-text-primary line-clamp-2 mb-1">{combo.title}</p>
                    <p className="text-xs text-text-muted">{combo.course_count} courses</p>
                    {combo.short_description && (
                      <p className="text-xs text-text-secondary line-clamp-2 mt-1">{combo.short_description}</p>
                    )}
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
 
        {/* Quick links */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link href={ROUTES.DASHBOARD_PROGRESS}>
            <Card variant="interactive" className="p-5 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary-subtle flex items-center justify-center text-primary flex-shrink-0">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">My Progress</p>
                <p className="text-xs text-text-muted">All enrolled courses</p>
              </div>
            </Card>
          </Link>
          <Link href={ROUTES.DASHBOARD_SAVED}>
            <Card variant="interactive" className="p-5 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-yellow-900/30 flex items-center justify-center text-yellow-400 flex-shrink-0">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">Saved Items</p>
                <p className="text-xs text-text-muted">Bookmarked courses & combos</p>
              </div>
            </Card>
          </Link>
          <Link href={ROUTES.COURSES}>
            <Card variant="interactive" className="p-5 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-green-900/30 flex items-center justify-center text-green-400 flex-shrink-0">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">Explore</p>
                <p className="text-xs text-text-muted">Find new courses</p>
              </div>
            </Card>
          </Link>
        </div>
      </div>
    </PageContainer>
  );
}
 