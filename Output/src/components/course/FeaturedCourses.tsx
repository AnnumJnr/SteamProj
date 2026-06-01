/**
 * components/course/FeaturedCourses.tsx
 * Fetches and renders featured courses for the homepage.
 * Client component — uses TanStack Query for data fetching.
 */

"use client";

import Link from "next/link";
import { useCourses } from "@/hooks/useCourses";
import { CourseCard } from "./CourseCard";
import { GridLayout } from "@/components/layout/GridLayout";
import { ErrorState } from "@/components/shared/ErrorState";
import { ROUTES } from "@/constants/routes";

export function FeaturedCourses() {
  const { data, isError, refetch } = useCourses({ page: 1 });

  if (isError) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  const courses = data?.results?.slice(0, 4) ?? [];

  if (courses.length === 0) {
    return (
      <div className="text-center py-12 text-text-muted text-sm">
        No courses available yet. The ingestion pipeline will populate these.
      </div>
    );
  }

  return (
    <GridLayout cols={4}>
      {courses.map((course) => (
        <Link key={course.id} href={ROUTES.COURSE_DETAIL(course.id)}>
          <CourseCard course={course} />
        </Link>
      ))}
    </GridLayout>
  );
}
