import { useEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
import { Banknote, Coins, ArrowDown } from "lucide-react";

import { markIntroComplete } from "./introSession";

/** An intentional, short transition for entering an already-authenticated workspace. */
export function WorkspaceEntryLink({
  to,
  animated,
  className,
  children,
}: {
  to: string;
  animated: boolean;
  className: string;
  children: ReactNode;
}) {
  const [entering, setEntering] = useState(false);
  const timer = useRef<number | null>(null);
  const navigate = useNavigate();

  useEffect(() => () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
  }, []);

  const enter = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!animated || event.defaultPrevented || event.button !== 0 ||
        event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (entering) return;
    markIntroComplete();
    setEntering(true);
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    timer.current = window.setTimeout(() => navigate(to), reducedMotion ? 80 : 950);
  };

  return (
    <>
      <Link to={to} className={className} onClick={enter}>{children}</Link>
      {entering && createPortal(
        <div className="v2-workspace-entry" role="status" aria-live="polite" aria-label="Opening your workspace">
          <div className="v2-workspace-entry-stage" aria-hidden="true">
            <div className="v2-workspace-entry-wallet"><span>S</span></div>
            <div className="v2-workspace-entry-coin v2-entry-coin-1"><Coins size={27} /></div>
            <div className="v2-workspace-entry-coin v2-entry-coin-2"><Banknote size={30} /></div>
            <div className="v2-workspace-entry-coin v2-entry-coin-3"><Coins size={24} /></div>
            <div className="v2-workspace-entry-coin v2-entry-coin-4"><Banknote size={25} /></div>
          </div>
          <p>Opening your workspace</p>
          <small>From payment to perspective <ArrowDown size={13} aria-hidden="true" /></small>
        </div>,
        document.body,
      )}
    </>
  );
}
