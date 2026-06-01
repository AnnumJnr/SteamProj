/**
 * components/ui/SkeletonCard.tsx
 * Skeleton placeholder card shown while course/combo data is loading.
 * Matches the visual height of CourseCard and ComboCard.
 */

import { cn } from "@/lib/utils";

interface SkeletonCardProps {
  className?: string;
}

function SkeletonLine({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-md shimmer-bg", className)} />
  );
}

export function SkeletonCourseCard({ className }: SkeletonCardProps) {
  return (
    <div className={cn(
      "bg-surface-raised border border-surface-border rounded-xl overflow-hidden",
      className
    )}>
      {/* Thumbnail skeleton */}
      <div className="aspect-video w-full shimmer-bg" />
      {/* Content */}
      <div className="p-4 space-y-3">
        <div className="flex gap-2">
          <SkeletonLine className="h-5 w-20" />
          <SkeletonLine className="h-5 w-16" />
        </div>
        <SkeletonLine className="h-4 w-full" />
        <SkeletonLine className="h-4 w-3/4" />
        <SkeletonLine className="h-3 w-full" />
        <SkeletonLine className="h-3 w-2/3" />
        <div className="flex justify-between pt-2 border-t border-surface-border">
          <SkeletonLine className="h-3 w-16" />
          <SkeletonLine className="h-3 w-12" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonComboCard({ className }: SkeletonCardProps) {
  return (
    <div className={cn(
      "bg-surface-raised border border-surface-border rounded-xl p-5 space-y-4",
      className
    )}>
      <div className="flex justify-between">
        <SkeletonLine className="h-4 w-28" />
        <SkeletonLine className="h-4 w-16" />
      </div>
      <div className="space-y-2">
        <SkeletonLine className="h-4 w-full" />
        <SkeletonLine className="h-4 w-3/4" />
      </div>
      <SkeletonLine className="h-3 w-full" />
      <SkeletonLine className="h-3 w-5/6" />
      <div className="flex gap-2">
        <SkeletonLine className="h-5 w-20 rounded-full" />
        <SkeletonLine className="h-5 w-16 rounded-full" />
      </div>
      <div className="flex justify-between pt-3 border-t border-surface-border">
        <SkeletonLine className="h-3 w-24" />
        <SkeletonLine className="h-3 w-16" />
      </div>
    </div>
  );
}
