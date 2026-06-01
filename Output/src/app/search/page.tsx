/**
 * app/search/page.tsx
 * Global search results page — searches both courses and combos.
 * Analytics: SEARCH_PERFORMED fired on query submission (OWNER: frontend).
 */

"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useCourses } from "@/hooks/useCourses";
import { useCombos } from "@/hooks/useCombos";
import { CourseCard } from "@/components/course/CourseCard";
import { ComboCard } from "@/components/combo/ComboCard";
import { PageContainer } from "@/components/layout/PageContainer";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ROUTES } from "@/constants/routes";
import { cn } from "@/lib/utils";

type ResultTab = "courses" | "combos";

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const [input, setInput] = useState(query);
  const [activeTab, setActiveTab] = useState<ResultTab>("courses");

  const { data: coursesData, isLoading: coursesLoading } = useCourses({ search: query });
  const { data: combosData, isLoading: combosLoading } = useCombos({ search: query });

  // Fire SEARCH_PERFORMED analytics event when query changes
  useEffect(() => {
    if (!query) return;
    if (typeof window !== "undefined" && (window as unknown as { posthog?: { capture: (e: string, p: Record<string, unknown>) => void } }).posthog) {
      (window as unknown as { posthog: { capture: (e: string, p: Record<string, unknown>) => void } }).posthog.capture("search_performed", {
        query,
        course_results: coursesData?.count ?? 0,
        combo_results: combosData?.count ?? 0,
      });
    }
  }, [query]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim()) {
      router.push(`${ROUTES.SEARCH}?q=${encodeURIComponent(input.trim())}`);
    }
  }

  const courses = coursesData?.results ?? [];
  const combos = combosData?.results ?? [];
  const isLoading = coursesLoading || combosLoading;

  return (
    <div className="py-8">
      {/* Search input */}
      <form onSubmit={handleSearch} className="mb-8 max-w-2xl">
        <div className="relative">
          <input
            type="search"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search courses, combos, topics…"
            autoFocus
            className="w-full px-4 py-3 pr-12 rounded-xl text-base bg-surface-raised border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-text-muted hover:text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
        </div>
      </form>

      {!query ? (
        <div className="text-center py-16">
          <p className="text-text-muted text-sm">Type to search courses and combo paths.</p>
        </div>
      ) : isLoading ? (
        <LoadingState message={`Searching for "${query}"…`} />
      ) : (
        <>
          {/* Tabs + count */}
          <div className="flex items-center gap-4 mb-6 border-b border-surface-border">
            {(["courses", "combos"] as ResultTab[]).map((tab) => {
              const count = tab === "courses" ? coursesData?.count ?? 0 : combosData?.count ?? 0;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "px-1 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px",
                    activeTab === tab
                      ? "border-primary text-primary"
                      : "border-transparent text-text-muted hover:text-text-secondary"
                  )}
                >
                  {tab} <span className="ml-1 text-xs text-text-muted">({count})</span>
                </button>
              );
            })}
          </div>

          {activeTab === "courses" && (
            courses.length === 0 ? (
              <EmptyState
                title={`No courses found for "${query}"`}
                description="Try a different search term or explore by category."
                action={{ label: "Browse all courses", onClick: () => router.push(ROUTES.COURSES) }}
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {courses.map((course) => (
                  <Link key={course.id} href={ROUTES.COURSE_DETAIL(course.id)}>
                    <CourseCard course={course} />
                  </Link>
                ))}
              </div>
            )
          )}

          {activeTab === "combos" && (
            combos.length === 0 ? (
              <EmptyState
                title={`No combos found for "${query}"`}
                description="Try a different search term or browse combo paths."
                action={{ label: "Browse all combos", onClick: () => router.push(ROUTES.COMBOS) }}
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {combos.map((combo) => (
                  <Link key={combo.id} href={ROUTES.COMBO_DETAIL(combo.id)}>
                    <ComboCard combo={combo} />
                  </Link>
                ))}
              </div>
            )
          )}
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <PageContainer>
      <Suspense fallback={<LoadingState className="py-24" />}>
        <SearchContent />
      </Suspense>
    </PageContainer>
  );
}
