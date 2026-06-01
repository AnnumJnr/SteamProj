/**
 * app/courses/page.tsx
 * Course listing page. Left sidebar filters + right content grid.
 * URL query params are the source of truth for active filters (useCourseFilters).
 *
 * Analytics: FILTER_APPLIED is fired from CourseFilters on filter change (OWNER: frontend).
 */

"use client";

import { Suspense } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { CourseFilters } from "@/components/course/CourseFilters";
import { CourseCard } from "@/components/course/CourseCard";
import { GridLayout } from "@/components/layout/GridLayout";
import { SkeletonCourseCard } from "@/components/ui/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useCourses } from "@/hooks/useCourses";
import { useCourseFilters } from "@/hooks/useCourseFilters";
import Link from "next/link";
import { ROUTES } from "@/constants/routes";
import { useState } from "react";

function CourseListingContent() {
  const { filters, updateFilter, clearFilters } = useCourseFilters();
  const { data, isLoading, isError, refetch } = useCourses(filters);
  const [searchInput, setSearchInput] = useState(filters.search || "");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    updateFilter("search", searchInput);
  }

  if (isError) {
    return (
      <ErrorState
        title="Couldn't load courses"
        message="There was a problem connecting to the server. Please try again."
        onRetry={() => refetch()}
      />
    );
  }

  const courses = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const hasMore = Boolean(data?.next);
  const currentPage = filters.page || 1;

  return (
    <div className="flex gap-8 py-8">

      {/* ─── Filter Sidebar ───────────────────────────────────────────────── */}
      <div className="hidden lg:block w-56 flex-shrink-0">
        <div className="sticky top-24">
          <CourseFilters
            filters={filters}
            onUpdate={updateFilter}
            onClear={clearFilters}
          />
        </div>
      </div>

      {/* ─── Main Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 min-w-0">

        {/* Search bar + results count */}
        <div className="flex items-center gap-4 mb-6 flex-wrap">
          <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 min-w-0 max-w-md">
            <div className="relative flex-1">
              <Input
                type="search"
                placeholder="Search courses…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="pr-10"
              />
              <button
                type="submit"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-primary transition-colors"
                aria-label="Search"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
            </div>
          </form>

          {!isLoading && (
            <p className="text-sm text-text-muted flex-shrink-0">
              {totalCount.toLocaleString()} {totalCount === 1 ? "course" : "courses"} found
            </p>
          )}
        </div>

        {/* Active filter chips */}
        {Object.entries(filters).some(([k, v]) => k !== "page" && k !== "search" && v) && (
          <div className="flex items-center gap-2 flex-wrap mb-5">
            {Object.entries(filters).map(([key, value]) => {
              if (key === "page" || key === "search" || !value) return null;
              return (
                <button
                  key={key}
                  onClick={() => updateFilter(key as keyof typeof filters, "")}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-primary-subtle text-primary border border-primary/20 hover:bg-primary-muted transition-colors"
                >
                  {String(value)}
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              );
            })}
          </div>
        )}

        {/* Course grid */}
        {isLoading ? (
          <GridLayout cols={3}>
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCourseCard key={i} />
            ))}
          </GridLayout>
        ) : courses.length === 0 ? (
          <EmptyState
            title="No courses found"
            description="Try adjusting your filters or search term."
            action={{ label: "Clear filters", onClick: clearFilters }}
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        ) : (
          <GridLayout cols={3}>
            {courses.map((course) => (
              <Link key={course.id} href={ROUTES.COURSE_DETAIL(course.id)}>
                <CourseCard course={course} />
              </Link>
            ))}
          </GridLayout>
        )}

        {/* Pagination */}
        {(data?.previous || hasMore) && (
          <div className="flex items-center justify-center gap-3 mt-10">
            <Button
              variant="secondary"
              size="sm"
              disabled={!data?.previous}
              onClick={() => updateFilter("page", String(Math.max(1, currentPage - 1)))}
            >
              ← Previous
            </Button>
            <span className="text-sm text-text-muted px-2">Page {currentPage}</span>
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasMore}
              onClick={() => updateFilter("page", String(currentPage + 1))}
            >
              Next →
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CoursesPage() {
  return (
    <PageContainer>
      {/* Page header */}
      <div className="pt-8 pb-2 border-b border-surface-border">
        <h1 className="text-3xl font-bold text-text-primary mb-1">All Courses</h1>
        <p className="text-sm text-text-secondary">
          Curated STEM courses from the world&apos;s best free learning providers
        </p>
      </div>

      <Suspense fallback={
        <div className="flex gap-8 py-8">
          <div className="hidden lg:block w-56 flex-shrink-0" />
          <GridLayout cols={3} className="flex-1">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCourseCard key={i} />
            ))}
          </GridLayout>
        </div>
      }>
        <CourseListingContent />
      </Suspense>
    </PageContainer>
  );
}
