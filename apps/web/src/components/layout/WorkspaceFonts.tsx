import { useEffect } from "react";

/** Activate the existing faces while the session loads; no second preload download. */
export function WorkspaceFonts() {
  useEffect(() => {
    if (!document.fonts?.load) return;
    for (const font of [
      "600 16px Manrope",
      "700 16px Manrope",
      '400 14px "DM Sans"',
      '500 14px "DM Sans"',
      '400 12px "IBM Plex Mono"',
    ]) {
      // Font loading is best-effort; preserve the browser's normal fallback on failure.
      void document.fonts.load(font).catch(() => undefined);
    }
  }, []);
  return null;
}
