import { clsx } from "clsx";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

const styles: Record<Variant, string> = {
  primary: "bg-accent-strong text-white hover:bg-[#3474d6] disabled:bg-raised disabled:text-fg-subtle",
  secondary: "border border-line-strong bg-raised text-fg hover:border-fg-subtle disabled:text-fg-subtle",
  ghost: "text-fg-muted hover:text-fg hover:bg-raised",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean; iconOnly?: boolean };

export function Button({ variant = "primary", busy = false, iconOnly = false, className, children, disabled, ...rest }: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium",
        iconOnly ? "size-9" : "h-9 px-3.5",
        "transition-colors duration-[var(--duration-fast)] disabled:cursor-not-allowed",
        styles[variant],
        className,
      )}
    >
      {busy && <Loader2 aria-hidden className="size-4 animate-spin" />}
      {children}
    </button>
  );
}
