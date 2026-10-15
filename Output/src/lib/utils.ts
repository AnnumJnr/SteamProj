/**
 * lib/utils.ts
 * General-purpose utility functions shared across the frontend.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatDuration(hours: number, minutes: number): string {
  if (hours === 0 && minutes === 0) return "—";
  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

export function formatRating(rating: number): string {
  return rating.toFixed(1);
}

export function formatRatingCount(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength).trimEnd() + "…";
}

/**
 * Extracts a YouTube video ID from any YouTube URL format.
 *
 * Handles all URL shapes that the ingestion pipeline produces:
 *   https://www.youtube.com/watch?v=abc123
 *   https://youtube.com/watch?v=abc123
 *   https://youtu.be/abc123
 *   https://www.youtube.com/embed/abc123
 *   https://www.youtube.com/playlist?list=PLxxx  → returns null (playlist, not video)
 *
 * Fix: the previous version had a corrupted hostname string
 * ("www.youtube.com" was embedded inside a markdown link literal)
 * which caused all www.youtube.com URLs to return null and the embed to never render.
 */
export function extractYouTubeId(url: string): string | null {
  if (!url) return null;

  try {
    const urlObj = new URL(url);

    // Short link: youtu.be/VIDEO_ID
    if (urlObj.hostname === "youtu.be") {
      const id = urlObj.pathname.slice(1).split("/")[0];
      return id || null;
    }

    // Standard and embed URLs: youtube.com and www.youtube.com
    if (
      urlObj.hostname === "www.youtube.com" ||
      urlObj.hostname === "youtube.com"
    ) {
      // Already an embed URL: /embed/VIDEO_ID
      if (urlObj.pathname.startsWith("/embed/")) {
        const id = urlObj.pathname.split("/embed/")[1]?.split("/")[0];
        return id || null;
      }

      // Standard watch URL: /watch?v=VIDEO_ID
      const v = urlObj.searchParams.get("v");
      if (v) return v;

      // Playlist-only URLs have no v param — cannot embed as a single video
      return null;
    }

    return null;
  } catch {
    // URL parsing failed — not a valid URL
    return null;
  }
}

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

export function formatProgress(percentage: number): string {
  if (percentage === 0) return "Not started";
  if (percentage === 100) return "Complete";
  return `${Math.round(percentage)}% complete`;
}