import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "./PageHeader";
import { Panel } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/States";

export function PaymentBackLink() {
  return (
    <Link
      to="/app/transactions"
      className="mb-4 inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-fg"
    >
      <ArrowLeft aria-hidden className="size-4" /> Transactions
    </Link>
  );
}

/** Reserve the actual record workspace, without hiding the shell or inventing data. */
export function RecordLoading({
  payment = false,
  navigation = false,
}: {
  payment?: boolean;
  navigation?: boolean;
}) {
  return (
    <>
      {navigation && <PaymentBackLink />}
      <div
        className="workspace-record-loading"
        role="status"
        aria-label={
          payment ? "Loading payment dossier" : "Loading transactions"
        }
      >
        {payment ? (
          <>
            <div className="casefile-record-heading">
              <p className="workspace-kicker">PAYMENT DOSSIER</p>
              <div className="workspace-page-heading">
                <div className="min-w-0">
                  <Skeleton className="payment-amount-placeholder w-64" />
                  <div className="workspace-page-description">
                    <Skeleton className="h-6 w-64" />
                  </div>
                </div>
              </div>
            </div>
            <div className="casefile-ledger" aria-hidden="true">
              <Panel title="PayPal references" className="casefile-facts">
                <Skeleton className="h-32" />
              </Panel>
              <Panel title="Risk assessment" className="risk-record">
                <div className="risk-content">
                  <Skeleton className="h-40" />
                </div>
              </Panel>
              <Panel title="Event timeline" className="casefile-timeline">
                <div className="space-y-3">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </Panel>
            </div>
          </>
        ) : (
          <>
            <PageHeader
              title="Transactions"
              description="Every PayPal order SENTINEL has created or reconciled. Select a row to open its record."
            />
            <div aria-hidden="true">
              <div className="workspace-toolbar">
                <Skeleton className="h-[42px] min-w-56 flex-1 sm:max-w-sm" />
                <Skeleton className="h-[42px] w-52" />
                <Skeleton className="h-[42px] w-52" />
              </div>
              <Skeleton className="transaction-grid w-full" />
            </div>
          </>
        )}
      </div>
    </>
  );
}
