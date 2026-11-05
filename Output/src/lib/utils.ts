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
 * What kind of YouTube player to embed, and the ID to embed it with.
 *  video    → https://www.youtube.com/embed/<id>
 *  playlist → https://www.youtube.com/embed/videoseries?list=<id>
 */
export type YouTubeEmbed =
  | { type: "video"; id: string }
  | { type: "playlist"; id: string };

/**
 * Extracts the embeddable YouTube target from any YouTube URL format.
 *
 * Handles all URL shapes that the ingestion pipeline produces:
 *   https://www.youtube.com/watch?v=abc123        → video
 *   https://youtube.com/watch?v=abc123            → video
 *   https://youtu.be/abc123                       → video
 *   https://www.youtube.com/embed/abc123          → video
 *   https://www.youtube.com/playlist?list=PLxxx   → playlist
 *
 * Playlists matter: the ingestion pipeline stores YouTube courses as
 * playlist URLs, so without playlist support nearly every YouTube course
 * falls back to a thumbnail instead of an embedded player.
 */
export function extractYouTubeEmbed(url: string): YouTubeEmbed | null {
  if (!url) return null;

  try {
    const urlObj = new URL(url);

    // Short link: youtu.be/VIDEO_ID
    if (urlObj.hostname === "youtu.be") {
      const id = urlObj.pathname.slice(1).split("/")[0];
      return id ? { type: "video", id } : null;
    }

    // Standard, embed, and playlist URLs: youtube.com and www.youtube.com
    if (
      urlObj.hostname === "www.youtube.com" ||
      urlObj.hostname === "youtube.com"
    ) {
      // Already an embed URL: /embed/VIDEO_ID
      if (urlObj.pathname.startsWith("/embed/")) {
        const id = urlObj.pathname.split("/embed/")[1]?.split("/")[0];
        return id ? { type: "video", id } : null;
      }

      // Playlist URL: /playlist?list=PLxxx (no v param)
      if (urlObj.pathname === "/playlist") {
        const list = urlObj.searchParams.get("list");
        return list ? { type: "playlist", id: list } : null;
      }

      // Standard watch URL: /watch?v=VIDEO_ID
      // A playlist param may accompany it; the video takes precedence.
      const v = urlObj.searchParams.get("v");
      if (v) return { type: "video", id: v };

      // /watch with only ?list=... (rare) still embeds as a playlist
      const list = urlObj.searchParams.get("list");
      return list ? { type: "playlist", id: list } : null;
    }

    return null;
  } catch {
    // URL parsing failed — not a valid URL
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
