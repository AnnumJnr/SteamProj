/**
 * constants/filters.ts
 * Static filter option arrays used in CourseFilters and ComboFilters dropdowns.
 * Values must match backend model choices exactly.
 * Source: apps/courses/models.py, apps/combos/models.py
 */

export interface FilterOption {
  label: string;
  value: string;
}

// ─── Course Filters ────────────────────────────────────────────────────────

export const STEM_CATEGORIES: FilterOption[] = [
  { label: "Computer Science", value: "Computer Science" },
  { label: "Mathematics", value: "Mathematics" },
  { label: "Natural Sciences", value: "Natural Sciences" },
  { label: "Engineering", value: "Engineering" },
  { label: "Technology & Applied Skills", value: "Technology & Applied Skills" },
  { label: "STEM Foundations", value: "STEM Foundations" },
];

export const COURSE_LEVELS: FilterOption[] = [
  { label: "Beginner", value: "Beginner" },
  { label: "Intermediate", value: "Intermediate" },
  { label: "Advanced", value: "Advanced" },
];

export const AGE_GROUPS: FilterOption[] = [
  { label: "Kids", value: "Kids" },
  { label: "Teens", value: "Teens" },
  { label: "Adults", value: "Adults" },
];

export const COURSE_PROVIDERS: FilterOption[] = [
  { label: "YouTube", value: "YouTube" },
  { label: "freeCodeCamp", value: "freeCodeCamp" },
  { label: "MIT OpenCourseWare", value: "MIT OCW" },
  { label: "OpenStax", value: "OpenStax" },
  { label: "CK-12", value: "CK-12" },
  { label: "Khan Academy", value: "Khan Academy" },
];

export const COURSE_FORMATS: FilterOption[] = [
  { label: "Video", value: "Video" },
  { label: "Text", value: "Text" },
  { label: "Interactive", value: "Interactive" },
];

// ─── Combo Filters ─────────────────────────────────────────────────────────

export const COMBO_DIFFICULTIES: FilterOption[] = [
  { label: "Beginner", value: "Beginner" },
  { label: "Intermediate", value: "Intermediate" },
  { label: "Advanced", value: "Advanced" },
  { label: "Mixed", value: "Mixed" },
];
