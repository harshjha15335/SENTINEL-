import { Banknote, CircleDollarSign } from "lucide-react";
import { Wallet } from "@/features/experience/Wallet";

/**
 * Login-only visual: banknotes and coins orbit the existing original vector
 * wallet. This does not represent a payment, balance or provider transaction.
 */
export function WalletOrbit() {
  return (
    <div className="auth-wallet-orbit" aria-hidden="true">
      <span className="auth-wallet-halo" />
      <span className="auth-money-ring auth-money-ring-back" />
      <span className="auth-money-ring auth-money-ring-front" />
      <div className="auth-money-track auth-money-track-one">
        <span className="auth-money-token auth-money-coin"><CircleDollarSign size={29} strokeWidth={1.65} /></span>
        <span className="auth-money-token auth-money-banknote"><Banknote size={28} strokeWidth={1.6} /></span>
      </div>
      <div className="auth-money-track auth-money-track-two">
        <span className="auth-money-token auth-money-coin"><CircleDollarSign size={25} strokeWidth={1.65} /></span>
        <span className="auth-money-token auth-money-banknote"><Banknote size={25} strokeWidth={1.6} /></span>
      </div>
      <div className="auth-wallet-object"><Wallet /></div>
      <span className="auth-money-star auth-money-star-one" />
      <span className="auth-money-star auth-money-star-two" />
      <span className="auth-money-star auth-money-star-three" />
    </div>
  );
}
