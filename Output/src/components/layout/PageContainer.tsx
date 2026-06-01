/**
 * components/layout/PageContainer.tsx
 * Consistent max-width wrapper with horizontal padding.
 * All pages that need bounded content width use this component.
 */

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface PageContainerProps {
  children: ReactNode;
  className?: string;
  narrow?: boolean; // For auth pages and single-column content
}

export function PageContainer({ children, className, narrow = false }: PageContainerProps) {
  return (
    <div
      className={cn(
        "w-full mx-auto px-4 sm:px-6 lg:px-8",
        narrow ? "max-w-2xl" : "max-w-7xl",
        className
      )}
    >
      {children}
    </div>
  );
}
