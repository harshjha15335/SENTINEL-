import "./experience.css";
import { Navigate, useLocation } from "react-router-dom";
import { useMe } from "@/features/auth/session";
import { ErrorState } from "@/components/ui/States";
import { AppNavigation } from "@/components/layout/AppNavigation";
import { DemoDossier } from "./Dossier";
import { MoneyStory } from "./Story";
/** Approved public experience. Authenticated services mount only under the application gate. */
export function MarketingHome() {
  return (
    <div className="sentinel-experience">
      <AppNavigation />
      <MoneyStory />
    </div>
  );
}
/** Protected wallet sequence after sign-in; no public route can unlock a workspace. */
export function AuthenticatedIntro() {
  const me = useMe();
  const location = useLocation();
  const requested = (location.state as { from?: unknown } | null)?.from;
  const destination = typeof requested === "string" && /^\/app(?:\/|$|\?)/.test(requested)
    ? requested
    : "/app";
  if (me.isPending) return <main className="experience-loading" role="status">Preparing your story…</main>;
  if (me.isError) return <main className="experience-loading"><ErrorState error={me.error} onRetry={() => void me.refetch()} /></main>;
  if (!me.data) return <Navigate to="/login" replace state={{ from: destination }} />;
  return (
    <div className="sentinel-experience">
      <AppNavigation />
      <MoneyStory workspaceTarget={destination} />
    </div>
  );
}
export function PublicDemoPayment() {
  return (
    <div className="sentinel-experience">
      <AppNavigation />
      <DemoDossier />
    </div>
  );
}
