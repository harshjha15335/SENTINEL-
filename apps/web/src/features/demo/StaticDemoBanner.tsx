import { useQuery } from "@tanstack/react-query";

import { formatDateTime } from "@/lib/format";
import { loadSnapshot } from "@/lib/staticApi";

const FULL_APP = "https://github.com/harshjha15335/SENTINEL-#launch-from-github";

/** Shown on every screen of the GitHub Pages build so no one mistakes the snapshot for a live system. */
export function StaticDemoBanner() {
  const q = useQuery({ queryKey: ["static-snapshot"], queryFn: loadSnapshot, staleTime: Infinity });
  return (
    <div role="note" aria-label="Static demo" className="border-b border-warning/40 bg-warning-soft px-4 py-2 text-xs text-fg md:px-8">
      <p>
        <span className="font-medium">Static demo, read only.</span>{" "}
        <span className="text-fg-muted">
          A snapshot of synthetic demonstration data (SYNTHETIC_DEMO)
          {q.data ? `, exported ${formatDateTime(q.data.generated_at)}` : ""}, viewed as a read-only viewer. There is no
          server here: nothing is saved, no PayPal call is made, and no payment shown is real.{" "}
          <a href={FULL_APP} className="text-fg underline underline-offset-2">
            Run the full app
          </a>
          .
        </span>
      </p>
    </div>
  );
}
