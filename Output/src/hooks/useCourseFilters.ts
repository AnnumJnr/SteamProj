/**
 * hooks/useCourseFilters.ts
 * Responsibility: manage course filter state synced to URL query params.
 * Filters are stored in the URL so filtered views are shareable and bookmarkable.
 * Forbidden: API calls, store writes.
 */

"use client";

import { useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { CourseFilters } from "@/types/course";

export function useCourseFilters(): {
  filters: CourseFilters;
  updateFilter: (key: keyof CourseFilters, value: string) => void;
  clearFilters: () => void;
} {
  const router = useRouter();
  const searchParams = useSearchParams();

  const filters: CourseFilters = {
    category: searchParams.get("category") || undefined,
    level: searchParams.get("level") || undefined,
    age_group: searchParams.get("age_group") || undefined,
    provider: searchParams.get("provider") || undefined,
    format: searchParams.get("format") || undefined,
    search: searchParams.get("search") || undefined,
    page: searchParams.get("page") ? Number(searchParams.get("page")) : undefined,
  };

  const updateFilter = useCallback(
    (key: keyof CourseFilters, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      // Reset page to 1 when filter changes
      if (key !== "page") {
        params.delete("page");
      }
      router.push(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const clearFilters = useCallback(() => {
    router.push("?", { scroll: false });
  }, [router]);

  return { filters, updateFilter, clearFilters };
}
