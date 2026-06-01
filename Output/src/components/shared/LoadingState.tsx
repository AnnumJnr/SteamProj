/**
 * components/shared/LoadingState.tsx
 * Generic loading spinner. Used when content shape is unknown or skeleton is not implemented.
 */

import { cn } from "@/lib/utils";

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = "Loading…", className }: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 text-text-secondary",
        className
      )}
      role="status"
      aria-label={message}
    >
      <svg
        className="animate-spin h-8 w-8 text-primary"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <p className="text-sm">{message}</p>
    </div>
  );
}
