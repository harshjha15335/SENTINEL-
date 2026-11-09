import { Link } from "react-router-dom";
import { ArrowUpRight, ArrowRight } from "lucide-react";
import { Workspace } from "./Dossier";
import { examples } from "./fixtures";
import { formatMoney } from "@/lib/format";
/** Interactive composition prototype, never an operational aggregate. */
export function CommandCenter() {
  return (
    <Workspace demo>
      <div className="v2-notice">
        INTERACTIVE COMPOSITION PROTOTYPE / SIMULATED
        <span>
          Two authored examples. No live queue, aggregate totals or model
          inference.
        </span>
      </div>
      <div className="v2-workspace-intro">
        <div>
          <p className="v2-eyebrow">COMMAND CENTER / DESIGN PREVIEW</p>
          <h1>
            Know what needs
            <br />
            <span>attention.</span>
          </h1>
        </div>
        <p>
          A calmer place to see the signal.
          <br />A clearer place to make the call.
        </p>
      </div>
      <div className="v2-decision-layout">
        <section className="v2-priority">
          <p className="v2-eyebrow">START WITH THE EXCEPTION</p>
          <span className="v2-classification v2-critical">
            HIGH RISK · ILLUSTRATIVE
          </span>
          <h2>
            A payment outside
            <br />
            the usual pattern.
          </h2>
          <p>DEMO-0148 · SIMULATED</p>
          <strong>
            $1,849.00 <small>USD</small>
          </strong>
          <dl>
            <div>
              <dt>Amount / merchant median</dt>
              <dd>8.4×</dd>
            </div>
            <div>
              <dt>Payments · past 24h</dt>
              <dd>7</dd>
            </div>
          </dl>
          <Link className="v2-button" to="/__v2-preview/dossier">
            Review the payment <ArrowUpRight size={18} />
          </Link>
          <p className="v2-fine">
            Illustrative priority, authored for this design preview.
          </p>
        </section>
        <section className="v2-review-queue">
          <div className="v2-section-heading">
            <h2>The review desk</h2>
            <span>2 DEMO RECORDS</span>
          </div>
          {examples.map((e, i) => (
            <Link
              key={e.id}
              className="v2-queue-row"
              to={`/__v2-preview/dossier?example=${i}`}
            >
              <span className="v2-queue-number">0{i + 1}</span>
              <div>
                <h3>{e.label}</h3>
                <p>{e.product} · SIMULATED</p>
              </div>
              <strong>
                {formatMoney(e.amount, "USD")}
                <small className={i === 0 ? "v2-critical" : ""}>
                  {e.band} RISK · ILLUSTRATIVE
                </small>
              </strong>
              <ArrowRight size={18} />
            </Link>
          ))}
          <div className="v2-editorial-note">
            <p className="v2-eyebrow">CONTEXT BEFORE CONCLUSIONS</p>
            <h3>
              A signal starts a question.
              <br />
              Your judgment comes next.
            </h3>
            <p>
              These examples demonstrate the decision hierarchy. Open authorized
              records to inspect existing merchant data.
            </p>
            <Link className="v2-text-link" to="/__v2-preview/workspace">
              Open transaction explorer <ArrowUpRight size={16} />
            </Link>
          </div>
        </section>
      </div>
      <section className="v2-activity">
        <h2>The example, in sequence.</h2>
        <ol>
          <li>
            <time>10:42</time>
            <div>
              <h3>Order created</h3>
              <p>Authored demonstration</p>
            </div>
          </li>
          <li>
            <time>10:43</time>
            <div>
              <h3>Capture recorded</h3>
              <p>Simulated payment</p>
            </div>
          </li>
          <li>
            <span>PREVIEW</span>
            <div>
              <h3>Context brought together</h3>
              <p>Illustrative risk, ready for review</p>
            </div>
          </li>
        </ol>
      </section>
    </Workspace>
  );
}
