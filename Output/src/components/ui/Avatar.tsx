/**
 * components/ui/Avatar.tsx
 * User avatar with initials fallback when no image is available.
 * No business logic. No domain knowledge.
 */

import Image from "next/image";
import { cn, getInitials } from "@/lib/utils";

type AvatarSize = "sm" | "md" | "lg";

interface AvatarProps {
  src?: string | null;
  name?: string | null;
  email?: string;
  size?: AvatarSize;
  className?: string;
}

const sizeStyles: Record<AvatarSize, { container: string; text: string }> = {
  sm: { container: "w-8 h-8 text-xs", text: "text-xs" },
  md: { container: "w-10 h-10", text: "text-sm" },
  lg: { container: "w-14 h-14", text: "text-base" },
};

export function Avatar({ src, name, email = "?", size = "md", className }: AvatarProps) {
  const { container, text } = sizeStyles[size];
  const initials = getInitials(name ?? null, email);

  return (
    <div
      className={cn(
        "relative rounded-full overflow-hidden flex-shrink-0",
        "flex items-center justify-center",
        "bg-primary-subtle border border-primary/30",
        container,
        className
      )}
    >
      {src ? (
        <Image
          src={src}
          alt={name || email}
          fill
          className="object-cover"
          sizes="56px"
        />
      ) : (
        <span className={cn("font-semibold text-primary", text)}>
          {initials}
        </span>
      )}
    </div>
  );
}
