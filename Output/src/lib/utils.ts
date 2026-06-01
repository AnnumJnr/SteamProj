/**
 * lib/utils.ts
 * General-purpose utility functions shared across the frontend.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges Tailwind class names safely, resolving conflicts.
 * Use this wherever className props are combined.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Formats a duration from hours + minutes into a human-readable string.
 * e.g. formatDuration(2, 30) → "2h 30m"
 *      formatDuration(0, 45) → "45m"
 *      formatDuration(3, 0)  → "3h"
 */
export function formatDuration(hours: number, minutes: number): string {
  if (hours === 0 && minutes === 0) return "—";
  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

/**
 * Formats a rating number to one decimal place.
 * e.g. formatRating(4.567) → "4.6"
 */
export function formatRating(rating: number): string {
  return rating.toFixed(1);
}

/**
 * Formats a rating count to a compact string.
 * e.g. formatRatingCount(12400) → "12.4k"
 */
export function formatRatingCount(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

/**
 * Truncates a string to a maximum character count, appending "…" if truncated.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength).trimEnd() + "…";
}

/**
 * Builds a YouTube video ID from a source URL.
 * Handles standard watch URLs and youtu.be short links.
 * Returns null if the URL cannot be parsed.
 */
export function extractYouTubeId(url: string): string | null {
  try {
    const urlObj = new URL(url);
    if (urlObj.hostname === "youtu.be") {
      return urlObj.pathname.slice(1);
    }
    if (
      urlObj.hostname === "www.youtube.com" ||
      urlObj.hostname === "youtube.com"
    ) {
      return urlObj.searchParams.get("v");
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Returns initials from a display name or email for avatar fallback.
 * e.g. "Alex Johnson" → "AJ"
 *      "alex@example.com" → "A"
 */
export function getInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name.trim().split(" ");
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }
    return parts[0][0].toUpperCase();
  }
  return email[0].toUpperCase();
}

/**
 * Converts a progress percentage to a display label.
 */
export function formatProgress(percentage: number): string {
  if (percentage === 0) return "Not started";
  if (percentage === 100) return "Complete";
  return `${Math.round(percentage)}% complete`;
}
