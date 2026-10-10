import { PayPalOneTimePaymentButton, PayPalProvider } from "@paypal/react-paypal-js/sdk-v6";
import { clsx } from "clsx";
import { CheckCircle2, FlaskConical, KeyRound, Minus, Plus } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { canOperate, useMe } from "@/features/auth/session";
import { usePayPalStatus } from "@/features/settings/usePayPalStatus";
import { newIdempotencyKey, type PayPalStatus, type Product, type Transaction } from "@/lib/api";
import { formatMoney } from "@/lib/format";

import { useCaptureOrder, useCreateOrder, useProducts } from "./useCheckout";

export function CheckoutPage() {
  const products = useProducts();
  const status = usePayPalStatus();
  const me = useMe();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [result, setResult] = useState<Transaction | null>(null);

  const selected = products.data?.find((p) => p.id === selectedId) ?? products.data?.[0] ?? null;

  return (
    <>
      <PageHeader
        title="Sandbox Checkout"
        description="A buyer-facing checkout for the demo merchant. The server sets the price, PayPal handles approval, and SENTINEL records only what PayPal confirms."
      />
      <div className="grid gap-4 lg:grid-cols-5">
        <Panel title="Catalogue" className="lg:col-span-3">
          {products.isPending && <Skeleton className="h-48" />}
          {products.isError && <ErrorState error={products.error} onRetry={() => void products.refetch()} />}
          {products.data?.length === 0 && <EmptyState title="No products">Run the seed command to create the demo catalogue.</EmptyState>}
          {products.data && products.data.length > 0 && (
            <fieldset>
              <legend className="sr-only">Choose a product</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {products.data.map((p) => (
                  <ProductOption
                    key={p.id}
                    product={p}
                    checked={selected?.id === p.id}
                    onSelect={() => {
                      setSelectedId(p.id);
                      setResult(null);
                    }}
                  />
                ))}
              </div>
            </fieldset>
          )}
        </Panel>
        <Panel title="Order" className="lg:col-span-2">
          {selected ? (
            <OrderSummary
              product={selected}
              quantity={quantity}
              setQuantity={(q) => {
                setQuantity(q);
                setResult(null);
              }}
            />
          ) : (
            <Skeleton className="h-24" />
          )}
          <div className="mt-5 border-t border-line pt-4">
            {result ? (
              <CaptureResult txn={result} onReset={() => setResult(null)} />
            ) : !canOperate(me.data?.role) ? (
              <p className="text-sm text-fg-muted">Your role is read-only. An admin or analyst can create orders.</p>
            ) : status.isPending ? (
              <Skeleton className="h-11" />
            ) : status.isError ? (
              <ErrorState error={status.error} />
            ) : selected ? (
              <PaymentArea status={status.data} product={selected} quantity={quantity} onCaptured={setResult} />
            ) : null}
          </div>
        </Panel>
      </div>
    </>
  );
}

function ProductOption({ product, checked, onSelect }: { product: Product; checked: boolean; onSelect: () => void }) {
  return (
    <label
      className={clsx(
        "flex cursor-pointer flex-col gap-1 rounded-md border p-3 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent",
        checked ? "border-accent bg-accent-soft" : "border-line hover:border-line-strong",
      )}
    >
      <input type="radio" name="product" className="sr-only" checked={checked} onChange={onSelect} />
      <span className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium">{product.name}</span>
        <span className="tabular text-sm">{formatMoney(product.price_minor, product.currency)}</span>
      </span>
      <span className="text-xs text-fg-muted">{product.description}</span>
      <span className="font-mono text-[11px] text-fg-subtle">{product.sku}</span>
    </label>
  );
}

function OrderSummary({ product, quantity, setQuantity }: { product: Product; quantity: number; setQuantity: (q: number) => void }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm">{product.name}</p>
        <div className="flex items-center gap-1" role="group" aria-label="Quantity">
          <Button variant="ghost" iconOnly aria-label="Decrease quantity" disabled={quantity <= 1} onClick={() => setQuantity(quantity - 1)}>
            <Minus aria-hidden className="size-4 text-fg" />
          </Button>
          <output aria-live="polite" className="tabular w-6 text-center text-sm">{quantity}</output>
          <Button variant="ghost" iconOnly aria-label="Increase quantity" disabled={quantity >= 10} onClick={() => setQuantity(quantity + 1)}>
            <Plus aria-hidden className="size-4 text-fg" />
          </Button>
        </div>
      </div>
      <div className="flex items-baseline justify-between">
        <p className="text-sm text-fg-muted">Total</p>
        <p className="tabular text-2xl font-semibold">{formatMoney(product.price_minor * quantity, product.currency)}</p>
      </div>
      <p className="text-xs text-fg-subtle">Estimate shown for convenience. The API recalculates the amount from the catalogue; the browser never sends a price.</p>
    </div>
  );
}

type PaymentProps = { status: PayPalStatus; product: Product; quantity: number; onCaptured: (t: Transaction) => void };

function PaymentArea(props: PaymentProps) {
  const { status } = props;
  if (status.mode === "fixture") return <SimulatedPayment {...props} />;
  if (!status.credentials_configured || !status.client_id) {
    return (
      <Notice icon={<KeyRound className="size-4 text-warning" />} title="PayPal sandbox credentials required">
        Set <code className="font-mono text-xs">SENTINEL_PAYPAL_CLIENT_ID</code> and{" "}
        <code className="font-mono text-xs">SENTINEL_PAYPAL_CLIENT_SECRET</code> from a PayPal Developer sandbox app, then restart the API. No
        payment can be taken until then.
      </Notice>
    );
  }
  if (status.token_check !== "ok") {
    return <Notice icon={<KeyRound className="size-4 text-critical" />} title="PayPal rejected the sandbox credentials">{status.token_error}</Notice>;
  }
  return <SandboxPayment {...props} clientId={status.client_id} />;
}

function useOrderFlow({ product, quantity, onCaptured }: Omit<PaymentProps, "status">) {
  const create = useCreateOrder();
  const capture = useCaptureOrder();
  const { notify } = useToast();
  const keyRef = useRef<{ key: string; sig: string } | null>(null);
  const sig = `${product.id}:${quantity}`;

  const createOrder = async (): Promise<string> => {
    // One idempotency key per product+quantity attempt; a retried click reuses the same order.
    if (!keyRef.current || keyRef.current.sig !== sig) keyRef.current = { key: newIdempotencyKey(), sig };
    const order = await create.mutateAsync({ productId: product.id, quantity, key: keyRef.current.key });
    return order.paypal_order_id;
  };
  const captureOrder = async (orderId: string) => {
    try {
      const txn = await capture.mutateAsync(orderId);
      keyRef.current = null;
      onCaptured(txn);
      notify(
        txn.status === "CAPTURED"
          ? txn.data_origin === "SIMULATED"
            ? { tone: "positive", title: "Simulated capture recorded", body: `${formatMoney(txn.amount_minor, txn.currency)}. No request reached PayPal.` }
            : { tone: "positive", title: "Payment captured", body: `${formatMoney(txn.amount_minor, txn.currency)} confirmed by PayPal sandbox.` }
          : { tone: "critical", title: "Capture not completed", body: txn.failure_reason ?? txn.status },
      );
    } catch (e) {
      notify({ tone: "critical", title: "Capture failed", body: e instanceof Error ? e.message : undefined });
    }
  };
  return { createOrder, captureOrder, create, capture };
}

function SandboxPayment({ clientId, ...props }: Omit<PaymentProps, "status"> & { clientId: string }) {
  const flow = useOrderFlow(props);
  const { notify } = useToast();
  const error = flow.create.error ?? flow.capture.error;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Pay with PayPal</p>
        <OriginBadge origin="LIVE_SANDBOX" />
      </div>
      <PayPalProvider clientId={clientId} environment="sandbox" components={["paypal-payments"]} pageType="checkout">
        <PayPalOneTimePaymentButton
          createOrder={async () => ({ orderId: await flow.createOrder() })}
          onApprove={async ({ orderId }) => {
            await flow.captureOrder(orderId);
          }}
          onCancel={() => notify({ tone: "critical", title: "Payment cancelled", body: "The buyer closed PayPal before approving." })}
          onError={(e: unknown) => notify({ tone: "critical", title: "PayPal error", body: e instanceof Error ? e.message : undefined })}
        />
      </PayPalProvider>
      {error && <ErrorState error={error} />}
      <p className="text-xs text-fg-subtle">Use a PayPal sandbox buyer account. No real money moves.</p>
    </div>
  );
}

function SimulatedPayment(props: Omit<PaymentProps, "status">) {
  const flow = useOrderFlow(props);
  const busy = flow.create.isPending || flow.capture.isPending;
  const error = flow.create.error ?? flow.capture.error;
  return (
    <div className="flex flex-col gap-3">
      <Notice icon={<FlaskConical className="size-4 text-warning" />} title="Simulated workflow">
        The API is running the offline fixture gateway. Orders and captures are created locally, labelled Simulated, and never reach
        PayPal.
      </Notice>
      <Button
        variant="secondary"
        busy={busy}
        onClick={async () => {
          try {
            const orderId = await flow.createOrder();
            await flow.captureOrder(orderId);
          } catch {
            /* surfaced via mutation error */
          }
        }}
      >
        Simulate buyer approval and capture
      </Button>
      {error && <ErrorState error={error} />}
    </div>
  );
}

function CaptureResult({ txn, onReset }: { txn: Transaction; onReset: () => void }) {
  const ok = txn.status === "CAPTURED";
  return (
    <div className="flex flex-col gap-3" role="status">
      <div className="flex items-center gap-2">
        {ok && <CheckCircle2 aria-hidden className="size-5 text-positive" />}
        <p className="text-sm font-medium">{ok ? "Capture confirmed" : "Capture needs attention"}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <StatusBadge status={txn.status} />
        <OriginBadge origin={txn.data_origin} />
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-fg-subtle">Order</dt>
        <dd className="truncate font-mono text-xs leading-5">{txn.paypal_order_id}</dd>
        <dt className="text-fg-subtle">Capture</dt>
        <dd className="truncate font-mono text-xs leading-5">{txn.paypal_capture_id ?? "—"}</dd>
      </dl>
      <div className="flex gap-2">
        <Link to={`/transactions/${txn.id}`} className="inline-flex h-9 items-center rounded-md bg-accent-strong px-3.5 text-sm font-medium text-white hover:bg-[#3474d6]">
          Open transaction
        </Link>
        <Button variant="ghost" onClick={onReset}>New order</Button>
      </div>
    </div>
  );
}

function Notice({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-line-strong bg-sunken p-3">
      <p className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
        {title === "Simulated workflow" && <Badge tone="warning">Not PayPal</Badge>}
      </p>
      <p className="mt-1.5 text-sm text-fg-muted">{children}</p>
    </div>
  );
}
