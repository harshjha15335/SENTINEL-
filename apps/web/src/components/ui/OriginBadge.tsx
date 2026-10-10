import * as Tooltip from "@radix-ui/react-tooltip";

import type { DataOrigin } from "@/lib/api";

const META: Record<DataOrigin, { label: string; explain: string; color: string }> = {
  LIVE_SANDBOX: {
    label: "Live sandbox",
    explain: "Created from an authenticated PayPal sandbox API response or a signature-verified webhook.",
    color: "var(--color-origin-sandbox)",
  },
  SIMULATED: {
    label: "Simulated",
    explain: "Produced by SENTINEL's offline fixture gateway. No request reached PayPal.",
    color: "var(--color-origin-simulated)",
  },
  SYNTHETIC_DEMO: {
    label: "Synthetic demo",
    explain: "Generated scenario data with a fixed seed, used to illustrate patterns sandbox checkout cannot produce.",
    color: "var(--color-origin-synthetic)",
  },
  MERCHANT_PROVIDED: {
    label: "Merchant provided",
    explain: "Supplied by the merchant (for example an uploaded document). Not verified by PayPal.",
    color: "var(--color-origin-merchant)",
  },
};

export function originLabel(origin: DataOrigin): string {
  return META[origin].label;
}

export function OriginBadge({ origin }: { origin: DataOrigin }) {
  const meta = META[origin];
  return (
    <Tooltip.Root delayDuration={150}>
      <Tooltip.Trigger asChild>
        <span
          tabIndex={0}
          className="inline-flex h-5 cursor-help items-center gap-1.5 rounded-sm border border-line-strong px-1.5 text-[11px] font-medium tracking-wide whitespace-nowrap text-fg-muted uppercase"
          aria-label={`Data origin: ${meta.label}. ${meta.explain}`}
        >
          <span aria-hidden className="size-1.5 rounded-full" style={{ background: meta.color }} />
          {meta.label}
        </span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          sideOffset={6}
          className="z-50 max-w-72 rounded-md border border-line-strong bg-raised px-3 py-2 text-xs leading-relaxed text-fg shadow-[var(--shadow-overlay)]"
        >
          {meta.explain}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
