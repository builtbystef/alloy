import type { CSSProperties, ElementType } from "react";

import { cn } from "@/lib/utils";

export type ShimmerProps = {
  children: string;
  as?: ElementType;
  className?: string;
  /** Seconds per sweep. */
  duration?: number;
};

/**
 * Text with a light band sweeping across it, for "Thinking…". CSS only: the
 * upstream element animates with `motion`, which this app does not ship.
 */
export const Shimmer = ({
  children,
  as: Component = "p",
  className,
  duration = 2,
}: ShimmerProps) => (
  <Component
    className={cn(
      "relative inline-block animate-[shimmer_var(--shimmer-duration)_linear_infinite] bg-[linear-gradient(90deg,var(--color-muted-foreground)_0%,var(--color-foreground)_50%,var(--color-muted-foreground)_100%)] bg-[length:200%_100%] bg-clip-text text-transparent",
      className,
    )}
    style={{ "--shimmer-duration": `${duration}s` } as CSSProperties}
  >
    {children}
  </Component>
);
