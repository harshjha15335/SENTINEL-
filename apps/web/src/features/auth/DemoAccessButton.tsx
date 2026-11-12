import { ArrowUpRight, Eye, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { STATIC_DEMO } from "@/lib/staticDemo";
import { useDemoLogin, useMe } from "./session";

/** Explicit click only; no automatic public login, shared passwords or auth bypass. */
export function DemoAccessButton({ className }: { className?: string }) {
  const navigate = useNavigate();
  const login = useDemoLogin();
  const me = useMe();

  if (STATIC_DEMO) {
    return (
      <Link className={className ?? "inline-flex items-center gap-2 text-sm text-accent"} to="/app">
        <Eye aria-hidden size={16} /> Explore read-only demo <ArrowUpRight aria-hidden size={14} />
      </Link>
    );
  }

  const open = () => {
    if (me.data) {
      navigate(me.data.merchant.environment === "DEMO" ? "/app/demo" : "/app");
      return;
    }
    login.mutate(undefined, {
      onSuccess: () => navigate("/app/demo", { replace: false }),
    });
  };

  return (
    <span className="inline-flex max-w-full flex-col items-start gap-1">
      <button
        type="button"
        className={className ?? "inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-line-strong px-5 py-2 text-sm font-medium text-fg transition hover:border-accent"}
        disabled={login.isPending || me.isPending}
        onClick={open}
      >
        {login.isPending ? <Loader2 aria-hidden size={16} className="animate-spin" /> : <Eye aria-hidden size={16} />}
        {login.isPending ? "Opening demo…" : "One-click judge demo"}
        <ArrowUpRight aria-hidden size={14} />
      </button>
      {login.isError && (
        <span role="alert" className="max-w-xs text-xs text-critical">
          Demo access is unavailable. You can still explore the public payment dossier or sign in normally.
        </span>
      )}
    </span>
  );
}
