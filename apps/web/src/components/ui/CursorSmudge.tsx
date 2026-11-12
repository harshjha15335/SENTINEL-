import { useEffect, useRef } from "react";

/**
 * A single soft lavender smudge following a fine pointer. No particles,
 * sparkles or text overlays; pure decorative background light.
 */
export function CursorSmudge() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!window.matchMedia?.("(pointer: fine)").matches) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const element = ref.current;
    if (!element) return;

    let currentX = -400, currentY = -400;
    let targetX = -400, targetY = -400;
    let frame = 0;
    let visible = false;
    const animate = () => {
      frame = 0;
      const dx = targetX - currentX;
      const dy = targetY - currentY;
      currentX += dx * 0.13;
      currentY += dy * 0.13;
      element.style.transform = `translate3d(${currentX - 155}px, ${currentY - 125}px, 0)`;
      if (Math.abs(dx) > 0.35 || Math.abs(dy) > 0.35) {
        frame = requestAnimationFrame(animate);
      }
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      targetX = event.clientX;
      targetY = event.clientY;
      if (!visible) {
        visible = true;
        currentX = targetX;
        currentY = targetY;
        element.style.opacity = "1";
      }
      if (!frame) frame = requestAnimationFrame(animate);
    };
    const hide = () => {
      visible = false;
      element.style.opacity = "0";
    };
    window.addEventListener("pointermove", move, { passive: true });
    document.addEventListener("pointerleave", hide);
    const onVisibility = () => { if (document.hidden) hide(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", move);
      document.removeEventListener("pointerleave", hide);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return <div className="sentinel-cursor-smudge" aria-hidden="true" />;
}
