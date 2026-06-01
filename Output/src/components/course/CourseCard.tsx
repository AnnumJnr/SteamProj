/**
 * components/course/CourseCard.tsx
 * Course card component used in grids. Renders thumbnail, title, metadata, and rating.
 * No data fetching. No navigation. Receives course data as a prop.
 *
 * API guarantee: thumbnail_url may be null — see backend: courses/serializers.py → CourseListSerializer
 * Optional chaining here is for TypeScript safety only, not a real edge case for thumbnail_url.
 */

import Image from "next/image";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDuration, formatRating, formatRatingCount, truncate } from "@/lib/utils";
import type { Course } from "@/types/course";

interface CourseCardProps {
  course: Course;
}

// Provider badge colours
const providerVariant = (provider: string): "primary" | "success" | "muted" | "warning" => {
  if (provider === "YouTube") return "primary";
  if (provider === "MIT OCW") return "success";
  if (provider === "freeCodeCamp") return "warning";
  return "muted";
};

// Level badge colours
const levelVariant = (level: string): "success" | "warning" | "danger" => {
  if (level === "Beginner") return "success";
  if (level === "Intermediate") return "warning";
  return "danger";
};

export function CourseCard({ course }: CourseCardProps) {
  return (
    <Card variant="interactive" className="flex flex-col h-full overflow-hidden">

      {/* Thumbnail */}
      <div className="relative aspect-video w-full bg-surface-overlay flex-shrink-0 overflow-hidden">
        {course.thumbnail_url ? (
          <Image
            src={course.thumbnail_url}
            alt={course.title}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          />
        ) : (
          // Fallback gradient when no thumbnail is available
          <div className="absolute inset-0 bg-gradient-to-br from-primary-subtle to-surface-overlay flex items-center justify-center">
            <svg className="w-10 h-10 text-primary/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        )}

        {/* Free badge overlay */}
        {course.is_free && (
          <div className="absolute top-2 left-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-accent text-white shadow-sm">
              Free
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col flex-1 p-4 gap-3">

        {/* Provider + Level badges */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge variant={providerVariant(course.provider)}>
            {course.provider}
          </Badge>
          <Badge variant={levelVariant(course.level)}>
            {course.level}
          </Badge>
        </div>

        {/* Title */}
        <h3 className="text-sm font-semibold text-text-primary line-clamp-2 leading-snug">
          {course.title}
        </h3>

        {/* Description */}
        <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed flex-1">
          {truncate(course.short_description, 120)}
        </p>

        {/* Meta row */}
        <div className="flex items-center justify-between pt-2 border-t border-surface-border">

          {/* Rating */}
          {course.rating_average > 0 ? (
            <div className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5 text-warning flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              <span className="text-xs font-semibold text-text-primary">
                {formatRating(course.rating_average)}
              </span>
              <span className="text-xs text-text-muted">
                ({formatRatingCount(course.rating_count)})
              </span>
            </div>
          ) : (
            <span className="text-xs text-text-muted">No rating</span>
          )}

          {/* Duration */}
          {(course.duration_hours > 0 || course.duration_minutes > 0) && (
            <div className="flex items-center gap-1 text-text-muted">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs">
                {formatDuration(course.duration_hours, course.duration_minutes)}
              </span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
