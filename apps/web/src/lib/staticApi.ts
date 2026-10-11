import { ApiError } from "./api";
import { STATIC_DEMO_REFUSAL } from "./staticDemo";

/*
 * Read-only stand-in for the API in the GitHub Pages build. Every file under demo-data/ is a
 * real API response exported by apps/api/scripts/export_static_demo.py from the demo loader;
 * this module only filters and pages those responses the same way the API does.
 */

type Row = Record<string, unknown>;
type Page = { items: Row[]; total: number; limit: number; offset: number };

const BASE = `${import.meta.env.BASE_URL}demo-data/`;
const ID = /^[0-9a-f-]{36}$/;
const cache = new Map<string, Promise<unknown>>();

function notFound(what: string): ApiError {
  return new ApiError(404, "not_found", `${what} not found`, {}, null);
}

function load<T>(name: string, what = "Resource"): Promise<T> {
  let p = cache.get(name);
  if (!p) {
    p = fetch(`${BASE}${name}.json`).then(async (r) => {
      if (r.status === 404) throw notFound(what);
      if (!r.ok) throw new ApiError(r.status, "http_error", `Could not load the demo snapshot (${r.status})`, {}, null);
      return (await r.json()) as unknown;
    });
    p.catch(() => cache.delete(name));
    cache.set(name, p);
  }
  return p as Promise<T>;
}

async function pick<T>(file: string, id: string, what: string): Promise<T> {
  const all = await load<Record<string, T>>(file);
  const hit = all[id];
  if (hit === undefined) throw notFound(what);
  return hit;
}

function page(rows: Row[], q: URLSearchParams): Page {
  const limit = Math.min(200, Math.max(1, Number(q.get("limit") ?? 50) || 50));
  const offset = Math.max(0, Number(q.get("offset") ?? 0) || 0);
  return { items: rows.slice(offset, offset + limit), total: rows.length, limit, offset };
}

function matches(row: Row, q: URLSearchParams, fields: Record<string, string>): boolean {
  return Object.entries(fields).every(([param, field]) => {
    const want = q.get(param);
    return !want || row[field] === want;
  });
}

async function transactions(q: URLSearchParams): Promise<Page> {
  // The export keeps the API's order (newest first), so filtering preserves it.
  const rows = await load<Row[]>("transactions");
  const term = q.get("q")?.trim().toLowerCase();
  const hit = (v: unknown) => typeof v === "string" && v.toLowerCase().includes(term ?? "");
  return page(
    rows.filter(
      (r) =>
        matches(r, q, { status: "status", data_origin: "data_origin" }) &&
        (!term || hit(r["paypal_order_id"]) || hit(r["paypal_capture_id"])),
    ),
    q,
  );
}

async function cases(q: URLSearchParams): Promise<Page> {
  const rows = await load<Row[]>("cases");
  const me = await load<{ id: string }>("me");
  return page(
    rows.filter(
      (r) =>
        matches(r, q, { status: "status", priority: "priority", data_origin: "data_origin", transaction_id: "transaction_id" }) &&
        (q.get("mine") !== "true" || (r["assignee"] as { id?: string } | null)?.id === me.id),
    ),
    q,
  );
}

const SINGLETONS: Record<string, string> = {
  "/me": "me",
  "/dashboard/summary": "dashboard",
  "/risk/model": "model",
  "/paypal/status": "paypal-status",
  "/products": "products",
};

export async function staticApi<T>(path: string, method: string): Promise<T> {
  if (method !== "GET") throw new ApiError(405, "static_demo", STATIC_DEMO_REFUSAL, {}, null);
  const url = new URL(path, "http://snapshot.invalid");
  const p = url.pathname;
  const q = url.searchParams;
  const parts = p.split("/").filter(Boolean);

  const single = SINGLETONS[p];
  if (single) return load<T>(single);
  if (p === "/audit") throw new ApiError(403, "forbidden", "The audit log is visible to admins only.", {}, null);
  if (p === "/transactions") return (await transactions(q)) as T;
  if (p === "/cases") return (await cases(q)) as T;

  const [kind, id, sub] = parts;
  if (id && ID.test(id) && parts.length <= 3) {
    if (kind === "transactions" && sub === undefined) {
      const [rows, extras] = await Promise.all([load<Row[]>("transactions"), load<Record<string, Row>>("transaction-extras")]);
      const row = rows.find((r) => r["id"] === id);
      if (!row) throw notFound("Transaction");
      return { ...row, ...extras[id] } as T;
    }
    if (kind === "transactions" && sub === "risk") return pick<T>("risk", id, "Risk assessment");
    if (kind === "cases" && sub === undefined) return pick<T>("case-details", id, "Case");
  }
  throw notFound("Resource");
}

export type Snapshot = {
  generated_at: string;
  commit: string | null;
  persona: { email: string; role: string };
  data_origins: string[];
  counts: { transactions: number; scored: number; cases: number };
};

export function loadSnapshot(): Promise<Snapshot> {
  return load<Snapshot>("snapshot");
}
