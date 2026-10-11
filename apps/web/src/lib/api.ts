import type { components } from "@contracts/openapi";

import { STATIC_DEMO } from "./staticDemo";

export type Schemas = components["schemas"];
export type Transaction = Schemas["TransactionOut"];
export type TransactionDetail = Schemas["TransactionDetailOut"];
export type TransactionPage = Schemas["Page_TransactionOut_"];
export type AuditPage = Schemas["Page_AuditOut_"];
export type Me = Schemas["MeOut"];
export type Session = Schemas["SessionOut"];
export type Product = Schemas["ProductOut"];
export type PayPalStatus = Schemas["PayPalStatusOut"];
export type DashboardSummary = Schemas["DashboardSummaryOut"];
export type OrderCreated = Schemas["OrderCreatedOut"];
export type DataOrigin = Transaction["data_origin"];
export type TransactionStatus = Transaction["status"];
export type Role = Me["role"];
export type RiskAssessment = Schemas["RiskAssessmentOut"];
export type RiskBand = RiskAssessment["risk_band"];
export type PolicyDecision = RiskAssessment["policy_decision"];
export type ModelCard = Schemas["ModelCardOut"];
export type ModelMetrics = Schemas["ModelMetricsOut"];
export type Case = Schemas["CaseOut"];
export type CaseDetail = Schemas["CaseDetailOut"];
export type CasePage = Schemas["Page_CaseOut_"];
export type CaseStatus = Case["status"];
export type CasePriority = Case["priority"];
export type CaseResolution = NonNullable<Case["resolution"]>;

export function isOperator(role: Role | undefined): boolean {
  return role === "ADMIN" || role === "ANALYST";
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly correlationId: string | null;

  constructor(status: number, code: string, message: string, details: Record<string, unknown>, cid: string | null) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
    this.correlationId = cid;
  }
}

function csrfToken(): string | undefined {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith("sentinel_csrf="))
    ?.split("=")[1];
}

type Options = { method?: "GET" | "POST"; body?: unknown; headers?: Record<string, string> };

export async function api<T>(path: string, { method = "GET", body, headers = {} }: Options = {}): Promise<T> {
  if (STATIC_DEMO) {
    // GitHub Pages build: no server. Reads come from the bundled snapshot; writes are refused.
    const { staticApi } = await import("./staticApi");
    return staticApi<T>(path, method);
  }
  const h: Record<string, string> = { Accept: "application/json", ...headers };
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (method !== "GET") {
    const token = csrfToken();
    if (token) h["X-CSRF-Token"] = decodeURIComponent(token);
  }
  const resp = await fetch(`/api/v1${path}`, {
    method,
    headers: h,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (resp.status === 204) return undefined as T;
  const text = await resp.text();
  const data: unknown = text ? JSON.parse(text) : null;
  if (!resp.ok) {
    const err = (data as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)?.error;
    throw new ApiError(
      resp.status,
      err?.code ?? "http_error",
      err?.message ?? `Request failed (${resp.status})`,
      err?.details ?? {},
      resp.headers.get("x-correlation-id"),
    );
  }
  return data as T;
}

export function newIdempotencyKey(): string {
  return `web-${crypto.randomUUID()}`;
}
