import {
  ArrowUpRight,
  Check,
  ChevronRight,
  FileText,
  Fingerprint,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useMe } from "@/features/auth/session";
import { useCases } from "@/features/cases/useCases";
import { useAssessment } from "@/features/risk/useRisk";
import {
  useTransaction,
  useTransactions,
} from "@/features/transactions/useTransactions";
import {
  ApiError,
  type DataOrigin,
  type TransactionStatus,
  type RiskAssessment,
  type TransactionDetail,
} from "@/lib/api";
import { formatMoney, humanize } from "@/lib/format";
import { examples, fixtureTransaction, FIXTURE_VERSION } from "./fixtures";

export function DemoDossier({ embedded = false }: { embedded?: boolean }) {
  const [params, setParams] = useSearchParams();
  const index = !embedded && params.get("example") === "1" ? 1 : 0;
  return (
    <Workspace demo embedded={embedded}>
      <div className="v2-notice">
        <span className="v2-dot" /> SIMULATED / PUBLIC-SAFE DEMONSTRATION{" "}
        <span>Illustrative scores. No inference or payment execution.</span>
      </div>
      <div className="v2-workspace-intro">
        <div>
          <p className="v2-eyebrow">TRANSACTIONS / PAYMENT ANALYSIS</p>
          <h1>
            Payment dossier<span>.</span>
          </h1>
        </div>
        <p>
          Follow the facts. Find the context.
          <br />A clear path to your next decision.
        </p>
      </div>
      <div
        className="v2-example-picker"
        role="group"
        aria-label="Demonstration transaction"
      >
        {examples.map((e, i) => (
          <button
            key={e.id}
            aria-pressed={index === i}
            onClick={() => setParams({ example: String(i) })}
          >
            <span className="v2-mono">0{i + 1}</span> {e.label}
            <ArrowUpRight size={15} />
          </button>
        ))}
      </div>
      <Dossier t={fixtureTransaction(index)} demoIndex={index} />
    </Workspace>
  );
}

export function AuthorizedWorkspace() {
  const me = useMe();
  const location = useLocation();
  if (me.isPending)
    return (
      <Workspace>
        <p role="status">Checking your existing session…</p>
      </Workspace>
    );
  if (me.isError)
    return (
      <Workspace>
        <QueryError error={me.error} retry={() => void me.refetch()} />
      </Workspace>
    );
  if (!me.data)
    return (
      <Workspace>
        <section className="v2-state">
          <ShieldCheck />
          <h1>Sign in to inspect real records.</h1>
          <p>
            This preview uses the existing session and merchant permissions.
          </p>
          <Link
            className="v2-button"
            to="/login"
            state={{ from: location.pathname + location.search }}
          >
            Sign in <ArrowUpRight size={16} />
          </Link>
        </section>
      </Workspace>
    );
  return (
    <Workspace>
      <div className="v2-notice">
        AUTHORIZED READ-ONLY PREVIEW{" "}
        <span>Existing merchant session · {me.data.role} · no mutations</span>
      </div>
      <LiveBrowser />
    </Workspace>
  );
}
function LiveBrowser() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const page = Math.max(0, Number(params.get("page")) || 0);
  const [descending, setDescending] = useState(false);
  const status = (params.get("status") ?? "") as TransactionStatus | "";
  const origin = (params.get("origin") ?? "") as DataOrigin | "";
  const q = useTransactions({
    page,
    pageSize: 10,
    q: params.get("q") ?? "",
    status,
    origin,
  });
  const changeFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    next.delete("page");
    next.delete("id");
    setParams(next);
  };
  const items = q.data
    ? [...q.data.items].sort((a, b) =>
        descending
          ? b.amount_minor - a.amount_minor
          : a.amount_minor - b.amount_minor,
      )
    : [];
  const id = params.get("id");
  return (
    <>
      <div className="v2-workspace-intro">
        <div>
          <p className="v2-eyebrow">YOUR MERCHANT WORKSPACE</p>
          <h1>
            Explore your transactions<span>.</span>
          </h1>
        </div>
      </div>
      <form
        className="v2-search"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          const next = new URLSearchParams(params);
          next.set("q", search);
          next.delete("page");
          next.delete("id");
          setParams(next);
        }}
      >
        <Search size={18} />
        <label className="v2-sr" htmlFor="preview-search">
          Search order or capture ID
        </label>
        <input
          id="preview-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search order or capture ID"
        />
        <label className="v2-sr" htmlFor="preview-status">
          Payment status
        </label>
        <select
          id="preview-status"
          value={status}
          onChange={(e) => changeFilter("status", e.target.value)}
        >
          <option value="">All statuses</option>
          {[
            "ORDER_CREATED",
            "CAPTURE_PENDING",
            "CAPTURED",
            "CAPTURE_DECLINED",
            "CAPTURE_FAILED",
            "REFUNDED",
            "PARTIALLY_REFUNDED",
          ].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
        <label className="v2-sr" htmlFor="preview-origin">
          Data origin
        </label>
        <select
          id="preview-origin"
          value={origin}
          onChange={(e) => changeFilter("origin", e.target.value)}
        >
          <option value="">All origins</option>
          {[
            "SIMULATED",
            "SYNTHETIC_DEMO",
            "MERCHANT_PROVIDED",
            "LIVE_SANDBOX",
          ].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
        <button className="v2-button" type="submit">
          Search
        </button>
      </form>
      {q.isPending && <p role="status">Loading transaction records…</p>}
      {q.isError && (
        <QueryError error={q.error} retry={() => void q.refetch()} />
      )}
      {q.data?.items.length === 0 && (
        <p className="v2-state">No transactions match this search.</p>
      )}
      {q.data && (
        <div className="v2-list-tools">
          <span>
            {q.data.total} records · page {page + 1}
            {q.isFetching ? " · Updating…" : ""}
          </span>
          <button onClick={() => setDescending(!descending)}>
            Amount {descending ? "descending" : "ascending"} · current page
          </button>
        </div>
      )}
      {q.data && (
        <div className="v2-live-list" aria-label="Transaction results">
          {items.map((t) => (
            <button
              aria-pressed={id === t.id}
              key={t.id}
              onClick={() => {
                const next = new URLSearchParams(params);
                next.set("id", t.id);
                setParams(next);
              }}
            >
              <span>{t.paypal_order_id ?? t.id}</span>
              <span>{formatMoney(t.amount_minor, t.currency)}</span>
              <span>{humanize(t.data_origin)}</span>
              <ChevronRight size={16} />
            </button>
          ))}
        </div>
      )}
      {q.data && (
        <div className="v2-list-tools">
          <button
            disabled={page === 0 || q.isFetching}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set("page", String(page - 1));
              setParams(next);
            }}
          >
            Previous page
          </button>
          <button
            disabled={(page + 1) * 10 >= q.data.total || q.isFetching}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set("page", String(page + 1));
              setParams(next);
            }}
          >
            Next page
          </button>
        </div>
      )}
      {id && <LiveDossier key={id} id={id} />}
    </>
  );
}
function LiveDossier({ id }: { id: string }) {
  const t = useTransaction(id);
  const risk = useAssessment(id);
  const cases = useCases({ transactionId: id, page: 0, pageSize: 10 });
  const sessionExpired = [t.error, risk.error, cases.error].some(
    (e) => e instanceof ApiError && e.status === 401,
  );
  if (sessionExpired)
    return (
      <p role="alert" className="v2-state">
        Your session expired.{" "}
        <Link
          to="/login"
          state={{
            from: `/__v2-preview/workspace?id=${encodeURIComponent(id)}`,
          }}
        >
          Sign in again
        </Link>
        .
      </p>
    );
  if (t.isPending) return <p role="status">Opening payment dossier…</p>;
  if (t.isError)
    return <QueryError error={t.error} retry={() => void t.refetch()} />;
  return (
    <>
      <Dossier t={t.data} assessment={risk.data} riskLoading={risk.isPending} />
      {risk.isError && (
        <QueryError error={risk.error} retry={() => void risk.refetch()} />
      )}
      <section className="v2-associated">
        <h2>Associated investigations</h2>
        {cases.isPending && <p role="status">Loading associated cases…</p>}
        {cases.isError && (
          <QueryError error={cases.error} retry={() => void cases.refetch()} />
        )}
        {cases.data?.items.length === 0 && (
          <p>No case is associated with this payment.</p>
        )}
        {cases.data?.items.map((c) => (
          <Link className="v2-case-link" to={`/cases/${c.id}`} key={c.id}>
            <FileText size={18} />
            <span>{c.title}</span>
            <span>{humanize(c.status)}</span>
            <ArrowUpRight size={18} />
          </Link>
        ))}
        <p className="v2-fine">
          Case links open the existing application. Its workflows remain intact
          during this prototype.
        </p>
      </section>
    </>
  );
}
export function QueryError({
  error,
  retry,
}: {
  error: Error;
  retry: () => void;
}) {
  return (
    <div role="alert" className="v2-state">
      <h2>Unable to load this record.</h2>
      <p>{error.message}</p>
      <button className="v2-button" onClick={retry}>
        Try again
      </button>
    </div>
  );
}
export function Workspace({
  children,
  demo = false,
  embedded = false,
}: {
  children: React.ReactNode;
  demo?: boolean;
  embedded?: boolean;
}) {
  const Content = embedded ? "div" : "main";
  return (
    <div className="v2-workspace">
      <header className="v2-global-header">
        <Link className="v2-wordmark" to="/__v2-preview">
          <span className="v2-brand-icon">S</span>SENTINEL
        </Link>
        <nav className="v2-global-nav" aria-label="Prototype workspace">
          <Link to="/__v2-preview/command-center">Command Center</Link>
          <Link
            to="/__v2-preview/workspace"
            aria-current={!demo ? "page" : undefined}
          >
            Transactions
          </Link>
          <Link to="/cases">
            Investigations <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
          <Link to="/model">
            Risk Intelligence <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
          <Link to="/policy">
            Policy Lab <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
          <Link to="/monitoring">
            Monitoring <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </nav>
        <details className="v2-mobile-menu">
          <summary>Menu</summary>
          <nav aria-label="Mobile workspace">
            <Link to="/__v2-preview/command-center">Command Center</Link>
            <Link to="/__v2-preview/workspace">Transactions</Link>
            <Link to="/__v2-preview/dossier">Demo dossier</Link>
            <Link to="/cases">
              Investigations <ArrowUpRight size={13} aria-hidden="true" />
            </Link>
            <Link to="/model">
              Risk Intelligence <ArrowUpRight size={13} aria-hidden="true" />
            </Link>
            <Link to="/policy">
              Policy Lab <ArrowUpRight size={13} aria-hidden="true" />
            </Link>
            <Link to="/monitoring">
              Monitoring <ArrowUpRight size={13} aria-hidden="true" />
            </Link>
            <Link to="/settings">
              Account <ArrowUpRight size={13} aria-hidden="true" />
            </Link>
            <Link to="/__v2-preview">Follow the money</Link>
          </nav>
        </details>
        <Link
          className="v2-account"
          to="/settings"
          aria-label="Account settings"
        >
          Account <ArrowUpRight size={13} aria-hidden="true" />
        </Link>
      </header>
      <Content className="v2-workspace-main">
        <div className="v2-workspace-top">
          <Link to="/__v2-preview/dossier">Demo dossier</Link>
          <span>
            {demo ? "SIMULATED PREVIEW" : "EXISTING MERCHANT SESSION"} ·
            Arrow-marked links open the existing application
          </span>
          <Link to="/__v2-preview">
            Follow the money <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </div>
        {children}
      </Content>
    </div>
  );
}
function Dossier({
  t,
  demoIndex,
  assessment,
  riskLoading = false,
}: {
  t: TransactionDetail;
  demoIndex?: number;
  assessment?: RiskAssessment | null;
  riskLoading?: boolean;
}) {
  const demo = demoIndex !== undefined;
  const example = demo ? examples[demoIndex] : undefined;
  const score = demo ? example?.score : assessment?.risk_score;
  const band = demo ? example?.band : assessment?.risk_band;
  const [tab, setTab] = useState("overview");
  const factors = example
    ? example.factors.map(([label, value, width]) => ({ label, value, width }))
    : (assessment?.explanation.contributions.slice(0, 6).map((c) => ({
        label: c.label,
        value: `${c.contribution >= 0 ? "+" : ""}${c.contribution.toFixed(3)} log-odds`,
        width: Math.min(100, Math.abs(c.contribution) * 35),
      })) ?? []);
  return (
    <article className="v2-dossier" aria-label="Payment dossier">
      <header className="v2-dossier-header">
        <div>
          <p className="v2-eyebrow">
            PAYMENT RECORD /{" "}
            {demo ? "DEMO-014" + (8 + (demoIndex ?? 0)) : t.id.slice(0, 8)}
          </p>
          <h2 data-shared-amount>
            {formatMoney(t.amount_minor, t.currency)} <span>{t.currency}</span>
          </h2>
          <p>
            {t.product_name ?? "Product unavailable"} <span>·</span>{" "}
            {t.payer_reference ?? "Payer unavailable"}
          </p>
        </div>
        <div className="v2-record-status">
          <span
            className={`v2-classification ${band === "HIGH" ? "v2-critical" : ""}`}
          >
            {band ? `${band} RISK` : "NOT SCORED"} ·{" "}
            {demo ? "ILLUSTRATIVE" : "RECORDED ASSESSMENT"}
          </span>
          <span className="v2-status">
            <Check size={13} />
            {humanize(t.status)}
          </span>
          <span className="v2-provenance">
            {humanize(t.data_origin)}
            {demo ? " · FIXTURE" : ""}
          </span>
          <time dateTime={t.occurred_at ?? t.created_at}>
            {new Date(t.occurred_at ?? t.created_at).toLocaleString("en-GB", {
              timeZone: "UTC",
              dateStyle: "medium",
              timeStyle: "short",
            })}{" "}
            UTC
          </time>
        </div>
      </header>
      <section className="v2-evidence-ledger" aria-label="Evidence sequence">
        <h3>The payment’s story</h3>
        <ol>
          {(demo
            ? [
                { at: "10:42 UTC", label: "Demo order created" },
                { at: "10:43 UTC", label: "Simulated capture recorded" },
              ]
            : [
                ...t.audit.map((a) => ({
                  at: a.created_at,
                  label: humanize(a.action.replaceAll(".", "_")),
                })),
                ...t.events.map((e) => ({
                  at: e.received_at,
                  label: e.provider_event_type,
                })),
              ]
          )
            .sort((a, b) => a.at.localeCompare(b.at))
            .slice(0, 4)
            .map((e, i) => (
              <li key={i}>
                <time>
                  {demo
                    ? e.at
                    : new Date(e.at).toLocaleTimeString("en-GB", {
                        timeZone: "UTC",
                      }) + " UTC"}
                </time>
                <strong>{e.label}</strong>
              </li>
            ))}
        </ol>
        {!demo && !t.audit.length && !t.events.length && (
          <p>No recorded events for this payment.</p>
        )}
      </section>
      <div className="v2-dossier-body">
        <section className="v2-facts">
          <div className="v2-tabs" role="group" aria-label="Dossier view">
            {["overview", "timeline"].map((s) => (
              <button
                aria-label={`${s} ${s === "overview" ? "01" : "02"}`}
                aria-pressed={tab === s}
                key={s}
                onClick={() => setTab(s)}
              >
                {s}
                <span>{s === "overview" ? "01" : "02"}</span>
              </button>
            ))}
          </div>
          {tab === "overview" ? (
            <>
              <div className="v2-section-label">
                <span>THE PAYMENT, IN DETAIL</span>
                <Fingerprint size={17} />
              </div>
              <dl className="v2-fact-grid">
                {[
                  ["Order reference", t.paypal_order_id],
                  ["Capture reference", t.paypal_capture_id],
                  ["Payment status", humanize(t.status)],
                  ["Quantity", String(t.quantity)],
                  ["Payer reference", t.payer_reference],
                  ["Data origin", humanize(t.data_origin)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value ?? "Unavailable"}</dd>
                  </div>
                ))}
              </dl>
              {t.failure_reason && <p role="alert">{t.failure_reason}</p>}
              <div className="v2-context-note">
                <ShieldCheck size={22} />
                <div>
                  <h3>Context before conclusions.</h3>
                  <p>
                    {demo
                      ? "This authored example demonstrates the interface. Its score and factors are illustrative; no PayPal event or model inference is claimed."
                      : "This record comes from your existing merchant API. Risk outputs describe model behavior, not the payer’s intent."}
                  </p>
                </div>
              </div>
              <div className="v2-dossier-foot">
                <span className="v2-mono">
                  {demo
                    ? FIXTURE_VERSION
                    : (assessment?.model_version ?? "NO VERIFIED MODEL OUTPUT")}
                </span>
                <span>
                  FOLLOW THE FACTS <ArrowUpRight size={13} />
                </span>
              </div>
            </>
          ) : (
            <section className="v2-timeline">
              <h3>Event timeline</h3>
              {demo ? (
                <ol>
                  <li>
                    <time>10:42 UTC</time>
                    <div>
                      <strong>Demonstration order created</strong>
                      <p>Authored fixture · no provider call</p>
                    </div>
                  </li>
                  <li>
                    <time>10:43 UTC</time>
                    <div>
                      <strong>Simulated capture recorded</strong>
                      <p>Interface demonstration only</p>
                    </div>
                  </li>
                </ol>
              ) : (
                <>
                  <ol>
                    {[
                      ...t.audit.map((a) => ({
                        at: a.created_at,
                        label: humanize(a.action.replaceAll(".", "_")),
                        detail: a.actor_type,
                      })),
                      ...t.events.map((e) => ({
                        at: e.received_at,
                        label: e.provider_event_type,
                        detail: `${e.verification_status} · ${e.processing_status}`,
                      })),
                    ]
                      .sort((a, b) => a.at.localeCompare(b.at))
                      .map((e, i) => (
                        <li key={i}>
                          <time dateTime={e.at}>
                            {new Date(e.at).toLocaleTimeString("en-GB", {
                              timeZone: "UTC",
                            })}{" "}
                            UTC
                          </time>
                          <div>
                            <strong>{e.label}</strong>
                            <p>{e.detail}</p>
                          </div>
                        </li>
                      ))}
                  </ol>
                  {!t.audit.length && !t.events.length && (
                    <p>No recorded events for this payment.</p>
                  )}
                </>
              )}
            </section>
          )}
        </section>
        <aside className="v2-risk" aria-label="Risk assessment">
          <div className="v2-section-label">
            <span>THE REASON TO LOOK CLOSER</span>
            <span className="v2-dot" />
          </div>
          <p className={`v2-risk-band ${band === "HIGH" ? "v2-critical" : ""}`}>
            {riskLoading
              ? "Loading assessment…"
              : band
                ? `${band} RISK`
                : "NOT SCORED"}
          </p>
          <div className="v2-score" data-shared-risk>
            {score === undefined ? "—" : Math.round(score * 100)}
            <span>{score === undefined ? "" : "/ 100"}</span>
          </div>
          <div className="v2-score-track" aria-hidden="true">
            <i style={{ width: `${(score ?? 0) * 100}%` }} />
          </div>
          <p className="v2-fine">
            {demo
              ? "Simulated example · illustrative score"
              : assessment
                ? `Model-generated · ${assessment.policy_mode} policy`
                : "No assessment has been returned."}
          </p>
          <h3>Behind the classification</h3>
          <ul className="v2-factors">
            {factors.map((f) => (
              <li key={f.label}>
                <div>
                  <span>{f.label}</span>
                  <strong>{f.value}</strong>
                </div>
                <div aria-hidden="true" className="v2-factor-track">
                  <i style={{ width: `${f.width}%` }} />
                </div>
              </li>
            ))}
          </ul>
          {assessment && (
            <>
              <p className="v2-fine">
                Contributions are in pre-calibration log-odds. Bar lengths show
                magnitude, not probability.
              </p>
              <p className="v2-policy">
                Shadow recommendation:{" "}
                <strong>{humanize(assessment.policy_decision)}</strong>
              </p>
              <details>
                <summary>Model limitations</summary>
                <ul>
                  {assessment.limitations.map((l) => (
                    <li key={l}>{l}</li>
                  ))}
                </ul>
              </details>
            </>
          )}
          <div className="v2-review-note">
            <FileText size={16} />
            <span>
              Decision support.
              <br />
              <strong>Human review remains essential.</strong>
            </span>
          </div>
        </aside>
      </div>
    </article>
  );
}
