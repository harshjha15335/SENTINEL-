import { useLayoutEffect, useRef } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

/** Application history restoration: path entry starts at the top; POP/reload restore saved position. */
export function AppNavigation() {
  const location = useLocation();
  const navigation = useNavigationType();
  const previousPath = useRef<string | null>(null);
  useLayoutEffect(() => {
    const key = `sentinel-app-scroll:${location.key}:${location.pathname}`;
    const samePath = previousPath.current === location.pathname;
    const entry = performance.getEntriesByType("navigation")[0] as
      PerformanceNavigationTiming | undefined;
    let saved: number | null = null;
    try {
      const value = sessionStorage.getItem(key);
      if (value !== null) saved = Number(value);
    } catch {
      /* Optional browser storage. */
    }
    const restore =
      navigation === "POP" &&
      (previousPath.current !== null ||
        entry?.type === "reload" ||
        entry?.type === "back_forward");
    const target =
      restore && saved !== null && Number.isFinite(saved)
        ? Math.max(0, saved)
        : samePath
          ? window.scrollY
          : 0;
    previousPath.current = location.pathname;
    let latest = target;
    let active = true;
    // Apply before paint so effect replays cannot mistake the outgoing scene's
    // position for a same-path scroll position and preserve it on the new page.
    window.scrollTo({ top: target, behavior: "instant" });
    const save = () => {
      try {
        sessionStorage.setItem(key, String(latest));
      } catch {
        /* Optional browser storage. */
      }
    };
    const onScroll = () => {
      latest = window.scrollY;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("pagehide", save);
    const frame = requestAnimationFrame(() => {
      if (!active) return;
      window.scrollTo({ top: target, behavior: "instant" });
      latest = window.scrollY;
    });
    return () => {
      active = false;
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("pagehide", save);
      save();
    };
  }, [location.key, location.pathname, navigation]);
  return null;
}
