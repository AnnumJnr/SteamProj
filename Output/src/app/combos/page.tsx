/**
 * app/combos/page.tsx
 * Combo listing page. Sidebar category filters + combo grid.
 * Analytics: COMBO_VIEWED fired on detail page only, not here.
 */

"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCombos } from "@/hooks/useCombos";
import { ComboCard } from "@/components/combo/ComboCard";
import { GridLayout } from "@/components/layout/GridLayout";
import { SkeletonComboCard } from "@/components/ui/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/layout/PageContainer";
import { ROUTES } from "@/constants/routes";
import { STEM_CATEGORIES, COMBO_DIFFICULTIES } from "@/constants/filters";
import { cn } from "@/lib/utils";
import type { ComboFilters } from "@/types/combo";

function ComboListingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const filters: ComboFilters = {
    category: searchParams.get("category") || undefined,
    difficulty: searchParams.get("difficulty") || undefined,
    recommended_age: searchParams.get("recommended_age") || undefined,
    search: searchParams.get("search") || undefined,
    page: searchParams.get("page") ? Number(searchParams.get("page")) : undefined,
  };

  const { data, isLoading, isError, refetch } = useCombos(filters);
  const [searchInput, setSearchInput] = useState(filters.search || "");

  function updateParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value); else params.delete(key);
    if (key !== "page") params.delete("page");
    router.push(`?${params.toString()}`, { scroll: false });
  }

  const combos = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const currentPage = filters.page || 1;

  if (isError) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  return (
    <div className="flex gap-8 py-8">

      {/* Sidebar */}
      <div className="hidden lg:block w-48 flex-shrink-0">
        <div className="sticky top-24 space-y-6">

          {/* Category filter */}
          <div>
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Subject</h4>
            <div className="space-y-0.5">
              <button
                onClick={() => updateParam("category", "")}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",
                  !filters.category ? "bg-primary-subtle text-primary font-medium" : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                )}
              >
                All Combos
              </button>
              {STEM_CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  onClick={() => updateParam("category", filters.category === cat.value ? "" : cat.value)}
                  className={cn(
                    "w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",
                    filters.category === cat.value
                      ? "bg-primary-subtle text-primary font-medium"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                  )}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty filter */}
          <div>
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Difficulty</h4>
            <div className="space-y-0.5">
              {COMBO_DIFFICULTIES.map((d) => (
                <button
                  key={d.value}
                  onClick={() => updateParam("difficulty", filters.difficulty === d.value ? "" : d.value)}
                  className={cn(
                    "w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",
                    filters.difficulty === d.value
                      ? "bg-primary-subtle text-primary font-medium"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                  )}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 min-w-0">
        {/* Search + count */}
        <div className="flex items-center gap-4 mb-6 flex-wrap">
          <form
            className="flex items-center gap-2 flex-1 min-w-0 max-w-md"
            onSubmit={(e) => { e.preventDefault(); updateParam("search", searchInput); }}
          >
            <div className="relative flex-1">
              <input
                type="search"
                placeholder="Search combo paths…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full px-3 py-2 pr-10 rounded-lg text-sm bg-surface-overlay border border-surface-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
              />
              <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-primary transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
            </div>
          </form>
          {!isLoading && (
            <p className="text-sm text-text-muted">{totalCount.toLocaleString()} paths found</p>
          )}
        </div>

        {isLoading ? (
          <GridLayout cols={3}>
            {Array.from({ length: 6 }).map((_, i) => <SkeletonComboCard key={i} />)}
          </GridLayout>
        ) : combos.length === 0 ? (
          <EmptyState
            title="No combo paths found"
            description="Try a different category or clear your filters."
            action={{ label: "Clear filters", onClick: () => router.push("?") }}
          />
        ) : (
          <GridLayout cols={3}>
            {combos.map((combo) => (
              <Link key={combo.id} href={ROUTES.COMBO_DETAIL(combo.id)}>
                <ComboCard combo={combo} />
              </Link>
            ))}
          </GridLayout>
        )}

        {/* Pagination */}
        {(data?.previous || data?.next) && (
          <div className="flex items-center justify-center gap-3 mt-10">
            <Button variant="secondary" size="sm" disabled={!data?.previous} onClick={() => updateParam("page", String(Math.max(1, currentPage - 1)))}>← Previous</Button>
            <span className="text-sm text-text-muted">Page {currentPage}</span>
            <Button variant="secondary" size="sm" disabled={!data?.next} onClick={() => updateParam("page", String(currentPage + 1))}>Next →</Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CombosPage() {
  return (
    <PageContainer>
      <div className="pt-8 pb-2 border-b border-surface-border flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary mb-1">All Combo Paths</h1>
          <p className="text-sm text-text-secondary">Structured learning sequences — beginner to job-ready</p>
        </div>
        <Link href={ROUTES.COMBO_CREATE}>
          <Button variant="secondary" size="sm">+ Create Combo</Button>
        </Link>
      </div>
      <Suspense fallback={<GridLayout cols={3} className="py-8">{Array.from({ length: 6 }).map((_, i) => <SkeletonComboCard key={i} />)}</GridLayout>}>
        <ComboListingContent />
      </Suspense>
    </PageContainer>
  );
}
