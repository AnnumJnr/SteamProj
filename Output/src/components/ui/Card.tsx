/**
 * components/ui/Card.tsx
 * Base card container. Variants: default | elevated | interactive.
 * Interactive variant implements approved hover behavior from architecture ruleset §8.1.
 * No business logic. No domain knowledge.
 */

import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type CardVariant = "default" | "elevated" | "interactive";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
}

const variantStyles: Record<CardVariant, string> = {
  default:
    "bg-surface-raised border border-surface-border rounded-xl",
  elevated:
    "bg-surface-raised border border-surface-border rounded-xl shadow-md",
  interactive:
    // Approved hover: border → primary, shadow → glow, translateY -2px (200ms ease-out)
    "bg-surface-raised border border-surface-border rounded-xl shadow-md " +
    "transition-all duration-200 ease-out cursor-pointer " +
    "hover:border-primary hover:shadow-glow hover:-translate-y-0.5",
};

export function Card({ variant = "default", className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(variantStyles[variant], className)}
      {...props}
    >
      {children}
    </div>
  );
}
