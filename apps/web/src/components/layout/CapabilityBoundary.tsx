import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  CAPABILITIES,
  FULL_APPLICATION_REQUIRED,
  supports,
  type Capability,
} from "@/lib/capabilities";

export function CapabilityBoundary({
  capability,
  children,
}: {
  capability: Capability;
  children: ReactNode;
}) {
  return supports(capability) ? (
    children
  ) : (
    <FullApplicationRequired capability={capability} />
  );
}
export function FullApplicationRequired({
  capability,
}: {
  capability: Capability;
}) {
  return (
    <section
      className="rounded-xl border border-line p-6"
      aria-label={`${CAPABILITIES[capability].title} availability`}
    >
      <h2 className="text-xl font-semibold">
        {CAPABILITIES[capability].title}
      </h2>
      <p className="mt-3 max-w-2xl text-sm text-fg-muted">
        {FULL_APPLICATION_REQUIRED}
      </p>
      <div className="mt-4 flex flex-wrap gap-5 text-sm">
        <Link to="/app" className="text-accent underline">
          Return to Command Center
        </Link>
        <Link to="/app/transactions" className="text-accent underline">
          Browse recorded payments
        </Link>
      </div>
    </section>
  );
}
