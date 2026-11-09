import "./experience.css";
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
export function PublicDemoPayment() {
  return (
    <div className="sentinel-experience">
      <AppNavigation />
      <DemoDossier />
    </div>
  );
}
