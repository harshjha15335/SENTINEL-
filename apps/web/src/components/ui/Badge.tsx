import { clsx } from "clsx";
import type { ReactNode } from "react";

export type Tone = "neutral" | "accent" | "positive" | "warning" | "critical";

const tones: Record<Tone, string> = {
  neutral: "border-line-strong text-fg-muted",
  accent: "border-accent/40 bg-accent-soft text-accent",
  positive: "border-positive/40 bg-positive-soft text-positive",
  warning: "border-warning/40 bg-warning-soft text-warning",
  critical: "border-critical/40 bg-critical-soft text-critical",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex min-h-6 items-center gap-1 rounded-full border px-2.5 text-[11px] font-medium tracking-normal whitespace-nowrap",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
