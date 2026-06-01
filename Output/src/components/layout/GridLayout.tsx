/**
 * components/layout/GridLayout.tsx
 * Reusable responsive grid. 1 → 2 → 3 → 4 columns.
 * Use this for all course and combo grids — never write raw grid classes in pages.
 */

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type GridCols = 2 | 3 | 4;

interface GridLayoutProps {
  children: ReactNode;
  cols?: GridCols;
  className?: string;
}

const colStyles: Record<GridCols, string> = {
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
};

export function GridLayout({ children, cols = 3, className }: GridLayoutProps) {
  return (
    <div className={cn("grid gap-6", colStyles[cols], className)}>
      {children}
    </div>
  );
}
