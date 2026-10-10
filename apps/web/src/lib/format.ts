const ZERO_DECIMAL = new Set(["HUF", "JPY", "TWD"]);

export function formatMoney(amountMinor: number, currency: string): string {
  const digits = ZERO_DECIMAL.has(currency) ? 0 : 2;
  const value = digits === 0 ? amountMinor : amountMinor / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(d);
}

export function shortId(id: string | null | undefined, keep = 8): string {
  if (!id) return "—";
  return id.length <= keep + 2 ? id : `${id.slice(0, keep)}…`;
}

export function humanize(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((w, i) => (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(" ");
}
