import { useEffect, type ReactNode } from "react";

/**
 * One motion boundary per workspace route. CSS handles route entry while a
 * lightweight observer progressively reveals data sections as they enter view.
 * No navigation, data fetching, focus management, or auth behavior changes.
 */
const REVEAL_SELECTOR = [
  ".workspace-page-heading",
  ".workspace-toolbar",
  ".workspace-section",
  ".workspace-inset",
  ".workspace-ledger > *",
  ".command-review-desk",
  ".command-queue-summary",
  ".command-focus",
  ".command-origin-row",
  ".sentinel-grid",
  ".workspace-list",
  "ul[aria-label='Cases'] > li",
  "[data-motion-reveal]",
].join(", ");

export function WorkspaceMotion({ children }: { children: ReactNode }) {
  useEffect(() => {
    // No wrapper element: direct-child selectors in existing workspace layouts
    // (monitoring, investigations, policy lab) must keep their original structure.
    const container = document.getElementById("main");
    if (!container || typeof IntersectionObserver === "undefined") return;
    // Accessibility: content remains visible and still works without motion.
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    container.classList.remove("workspace-route-enter");
    void container.offsetWidth; // restart CSS page transition on a pathname change
    container.classList.add("workspace-route-enter");

    const visible = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("workspace-motion-visible");
          visible.unobserve(entry.target);
        }
      },
      { rootMargin: "0px 0px -6% 0px", threshold: 0.05 },
    );

    let sequence = 0;
    const findNewSections = () => {
      container.querySelectorAll<HTMLElement>(REVEAL_SELECTOR).forEach((node) => {
        if (node.dataset.motionReady || node.closest("[data-motion-skip]")) return;
        node.dataset.motionReady = "true";
        node.style.setProperty("--motion-delay", `${(sequence++ % 4) * 55}ms`);
        node.classList.add("workspace-motion-reveal");
        visible.observe(node);
      });
    };
    findNewSections();

    // Queries render asynchronously. Observe new panels and KPI content without
    // rerendering React or touching the grid's virtualized cells.
    let pending = 0;
    const changes = new MutationObserver(() => {
      if (pending) return;
      pending = window.requestAnimationFrame(() => {
        pending = 0;
        findNewSections();
      });
    });
    changes.observe(container, { childList: true, subtree: true });

    return () => {
      changes.disconnect();
      visible.disconnect();
      if (pending) window.cancelAnimationFrame(pending);
      container.classList.remove("workspace-route-enter");
    };
  }, []);

  return <>{children}</>;
}
