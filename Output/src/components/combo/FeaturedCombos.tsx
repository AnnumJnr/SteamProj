/**
 * components/combo/FeaturedCombos.tsx
 * Fetches and renders featured combos for the homepage.
 * Client component — uses TanStack Query for data fetching.
 */

"use client";

import Link from "next/link";
import { useCombos } from "@/hooks/useCombos";
import { ComboCard } from "./ComboCard";
import { GridLayout } from "@/components/layout/GridLayout";
import { ErrorState } from "@/components/shared/ErrorState";
import { ROUTES } from "@/constants/routes";

export function FeaturedCombos() {
  const { data, isError, refetch } = useCombos({ page: 1 });

  if (isError) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  const combos = data?.results?.slice(0, 4) ?? [];

  if (combos.length === 0) {
    return (
      <div className="text-center py-12 text-text-muted text-sm">
        No combo paths available yet. Check back soon.
      </div>
    );
  }

  return (
    <GridLayout cols={4}>
      {combos.map((combo) => (
        <Link key={combo.id} href={ROUTES.COMBO_DETAIL(combo.id)}>
          <ComboCard combo={combo} />
        </Link>
      ))}
    </GridLayout>
  );
}
