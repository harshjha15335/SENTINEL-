import { useEffect, useRef } from "react";

type Speck = {
  x: number;
  y: number;
  dx: number;
  dy: number;
  age: number;
  life: number;
  radius: number;
  color: string;
};

/**
 * Decorative cursor sparkle, intentionally bounded (36 particles maximum).
 * No pointer interception, no animation on touch devices or reduced-motion.
 * Canvas is cleaned up on route unmount and when the tab is hidden.
 */
export function CursorGlitter() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!window.matchMedia?.("(pointer: fine)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let frame = 0;
    let last = 0;
    let lastSpawn = 0;
    let particles: Speck[] = [];
    const palette = ["#7547EB", "#9B72F1", "#B997FF", "#E9D8FF", "#FFFFFF"];

    const resize = () => {
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.ceil(window.innerWidth * scale);
      canvas.height = Math.ceil(window.innerHeight * scale);
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
    };

    const draw = (time: number) => {
      frame = 0;
      if (document.hidden) return;
      const elapsed = last ? Math.min(33, time - last) : 16;
      last = time;
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      particles = particles.filter((p) => p.age < p.life);
      for (const p of particles) {
        p.age += elapsed;
        p.x += p.dx * (elapsed / 16);
        p.y += p.dy * (elapsed / 16);
        p.dy += 0.015;
        const opacity = Math.max(0, 1 - p.age / p.life);
        ctx.globalAlpha = opacity * 0.85;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * (0.6 + opacity * 0.4), 0, Math.PI * 2);
        ctx.fill();
        if (p.radius > 1.3) {
          ctx.lineWidth = 0.65;
          ctx.strokeStyle = p.color;
          ctx.beginPath();
          ctx.moveTo(p.x - p.radius * 2.3, p.y);
          ctx.lineTo(p.x + p.radius * 2.3, p.y);
          ctx.moveTo(p.x, p.y - p.radius * 2.3);
          ctx.lineTo(p.x, p.y + p.radius * 2.3);
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
      if (particles.length) frame = requestAnimationFrame(draw);
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType === "touch" || document.hidden) return;
      const now = performance.now();
      if (now - lastSpawn < 26) return;
      lastSpawn = now;
      for (let n = 0; n < 3; n++) {
        const direction = Math.random() * Math.PI * 2;
        const speed = 0.35 + Math.random() * 1.8;
        particles.push({
          x: event.clientX + (Math.random() - 0.5) * 18,
          y: event.clientY + (Math.random() - 0.5) * 18,
          dx: Math.cos(direction) * speed,
          dy: Math.sin(direction) * speed - 0.55,
          radius: 0.85 + Math.random() * 1.9,
          age: 0,
          life: 300 + Math.random() * 430,
          color: palette[Math.floor(Math.random() * palette.length)],
        });
      }
      if (particles.length > 36) particles = particles.slice(-36);
      if (!frame) frame = requestAnimationFrame(draw);
    };
    const visibility = () => {
      if (!document.hidden) return;
      cancelAnimationFrame(frame);
      frame = 0;
      particles = [];
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    };
    resize();
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", move, { passive: true });
    document.addEventListener("visibilitychange", visibility);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", move);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  return <canvas ref={ref} className="sentinel-cursor-glitter" aria-hidden="true" />;
}
