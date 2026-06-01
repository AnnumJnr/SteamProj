/**
 * components/course/CourseFilters.tsx
 * Course filter sidebar. Renders filter options and dispatches URL param updates.
 * No data fetching. Calls updateFilter from useCourseFilters hook.
 *
 * FIRED FROM: Filter changes dispatch FILTER_APPLIED event to PostHog
 * Source: constants/events.ts → FILTER_APPLIED (OWNER: frontend)
 */

"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import {
  STEM_CATEGORIES,
  COURSE_LEVELS,
  AGE_GROUPS,
  COURSE_PROVIDERS,
  COURSE_FORMATS,
  type FilterOption,
} from "@/constants/filters";
import type { CourseFilters } from "@/types/course";

interface CourseFiltersProps {
  filters: CourseFilters;
  onUpdate: (key: keyof CourseFilters, value: string) => void;
  onClear: () => void;
}

interface FilterGroupProps {
  title: string;
  options: FilterOption[];
  activeValue?: string;
  filterKey: keyof CourseFilters;
  onUpdate: (key: keyof CourseFilters, value: string) => void;
}

function FilterGroup({ title, options, activeValue, filterKey, onUpdate }: FilterGroupProps) {
  return (
    <div className="py-4 border-b border-surface-border last:border-b-0">
      <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        {title}
      </h4>
      <div className="space-y-1">
        {options.map((option) => {
          const isActive = activeValue === option.value;
          return (
            <button
              key={option.value}
              onClick={() => onUpdate(filterKey, isActive ? "" : option.value)}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all duration-150 text-left",
                isActive
                  ? "bg-primary-subtle text-primary font-medium"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
              )}
            >
              <span>{option.label}</span>
              {isActive && (
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function CourseFilters({ filters, onUpdate, onClear }: CourseFiltersProps) {
  const hasActiveFilters = Object.entries(filters).some(
    ([key, val]) => key !== "page" && key !== "search" && Boolean(val)
  );

  return (
    <aside className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 pb-3 border-b border-surface-border">
        <h3 className="text-sm font-semibold text-text-primary">Filters</h3>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={onClear} className="text-xs text-text-muted">
            Clear all
          </Button>
        )}
      </div>

      {/* Filter groups */}
      <FilterGroup
        title="Subjects"
        options={STEM_CATEGORIES}
        activeValue={filters.category}
        filterKey="category"
        onUpdate={onUpdate}
      />
      <FilterGroup
        title="Level"
        options={COURSE_LEVELS}
        activeValue={filters.level}
        filterKey="level"
        onUpdate={onUpdate}
      />
      <FilterGroup
        title="Age Group"
        options={AGE_GROUPS}
        activeValue={filters.age_group}
        filterKey="age_group"
        onUpdate={onUpdate}
      />
      <FilterGroup
        title="Provider"
        options={COURSE_PROVIDERS}
        activeValue={filters.provider}
        filterKey="provider"
        onUpdate={onUpdate}
      />
      <FilterGroup
        title="Format"
        options={COURSE_FORMATS}
        activeValue={filters.format}
        filterKey="format"
        onUpdate={onUpdate}
      />
    </aside>
  );
}
