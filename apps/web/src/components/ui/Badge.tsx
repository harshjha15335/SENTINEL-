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

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex h-5 items-center gap-1 rounded-sm border px-1.5 text-[11px] font-medium tracking-wide whitespace-nowrap uppercase",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
