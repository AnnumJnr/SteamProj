/**
 * components/shared/EmptyState.tsx
 * Generic empty state with optional call-to-action.
 */

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 py-16 text-center",
        className
      )}
    >
      {icon && (
        <div className="w-12 h-12 rounded-full bg-surface-overlay flex items-center justify-center text-text-muted">
          {icon}
        </div>
      )}
      <div>
        <h3 className="text-base font-semibold text-text-primary mb-1">{title}</h3>
        {description && (
          <p className="text-sm text-text-secondary max-w-sm">{description}</p>
        )}
      </div>
      {action && (
        <Button variant="primary" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
