/**
 * components/ui/Badge.tsx
 * Semantic badge/tag component.
 * Variants: default | success | warning | danger | muted | primary.
 * No business logic. No domain knowledge.
 */

import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "muted" | "primary";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-surface-overlay text-text-secondary border border-surface-border",
  primary: "bg-primary-muted text-primary border border-primary/20",
  success: "bg-accent-muted text-accent border border-accent/20",
  warning: "bg-yellow-900/40 text-warning border border-warning/20",
  danger: "bg-red-900/40 text-danger border border-danger/20",
  muted: "bg-surface-raised text-text-muted border border-surface-border",
};

export function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5",
        "text-xs font-medium rounded-full",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
