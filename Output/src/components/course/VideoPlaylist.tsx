/**
 * components/course/VideoPlaylist.tsx
 * Playlist sidebar for playlist-backed YouTube courses.
 *
 * Data source: GET /courses/{id}/ → CourseDetail.videos (ingested from
 * YouTube playlistItems by the backend pipeline). Never rendered when the
 * gate is locked — the parent page only mounts it after video_access_granted.
 */

import Image from "next/image";
import type { CourseVideoItem } from "@/types/course";

interface VideoPlaylistProps {
  videos: CourseVideoItem[];
  activeId: string | null;
  onSelect: (videoId: string) => void;
  completed?: boolean;
}

function formatSeconds(seconds: number | null): string | null {
  if (seconds === null || seconds <= 0) return null;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * Embed-friendly i.ytimg URLs are fine with next/image's configured
 * hostnames (next.config.ts remotePatterns) — fall back to unoptimized
 * <img> semantics via the `unoptimized` flag to match the course page.
 */
export function VideoPlaylist({
  videos,
  activeId,
  onSelect,
  completed = false,
}: VideoPlaylistProps) {
  if (videos.length === 0) return null;

  return (
    <div className="rounded-xl border border-surface-border bg-surface-overlay">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
        <h2 className="text-sm font-semibold text-text-primary">Course lessons</h2>
        <span className="text-xs text-text-muted">
          {videos.length} video{videos.length === 1 ? "" : "s"}
        </span>
      </div>
      <ul className="max-h-[420px] overflow-y-auto divide-y divide-surface-border">
        {videos.map((video, index) => {
          const isActive = video.video_id === activeId;
          const duration = formatSeconds(video.duration_seconds);
          return (
            <li key={video.id}>
              <button
                type="button"
                onClick={() => onSelect(video.video_id)}
                aria-current={isActive}
                className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-raised ${
                  isActive ? "bg-primary/5" : ""
                }`}
              >
                <span
                  className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full border text-[10px] leading-[18px] text-center ${
                    isActive
                      ? "border-primary bg-primary text-white"
                      : "border-surface-border text-text-muted"
                  }`}
                >
                  {index + 1}
                </span>
                <span className="relative flex-shrink-0 w-16 h-9 rounded-md overflow-hidden bg-surface-raised">
                  {video.thumbnail_url && (
                    <Image
                      src={video.thumbnail_url}
                      alt=""
                      fill
                      className="object-cover"
                      sizes="64px"
                      unoptimized
                    />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  <span
                    className={`block text-xs font-medium leading-snug line-clamp-2 ${
                      isActive ? "text-primary" : "text-text-primary"
                    }`}
                  >
                    {video.title}
                  </span>
                  {(duration || completed) && (
                    <span className="mt-0.5 block text-[10px] text-text-muted">
                      {duration ? `${duration} min` : ""}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
