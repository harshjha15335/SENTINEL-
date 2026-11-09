export const clamp = (x: number) => Math.min(1, Math.max(0, x));
export const phase = (p: number, a: number, b: number) =>
  clamp((p - a) / (b - a));
export const ease = (x: number) => x * x * (3 - 2 * x);
export const mix = (a: number, b: number, t: number) => a + (b - a) * t;
export const chapters = [0, 0.12, 0.27, 0.43, 0.57, 0.72, 0.9] as const;
/** Authored paths, never random. The main receipt is one persistent object. */
export function moneyScene(progress: number) {
  const p = clamp(progress),
    release = ease(phase(p, 0.13, 0.34)),
    journey = ease(phase(p, 0.3, 0.62));
  const isolate = ease(phase(p, 0.43, 0.57)),
    assemble = ease(phase(p, 0.76, 0.99));
  return {
    p,
    open: ease(phase(p, 0.08, 0.24)),
    release,
    isolate,
    assemble,
    wallet: {
      x: mix(735, 1050, release),
      y: mix(270, 90, release),
      scale: mix(1, 0.48, release),
      angle: mix(-8, 7, release),
      opacity: 1 - ease(phase(p, 0.38, 0.54)),
    },
    receipt: {
      x:
        mix(1040, 975, release) +
        60 * journey -
        95 * Math.sin(journey * Math.PI),
      y: mix(430, 230, release) + 210 * journey,
      angle: mix(-18, 0, isolate),
      scale: mix(0.15, 1, release),
      opacity: ease(phase(p, 0.13, 0.19)) * (1 - ease(phase(p, 0.78, 0.82))),
    },
    stage: chapters.reduce<number>((last, b, i) => (p >= b ? i : last), 0),
    field: ease(phase(p, 0.53, 0.61)) * (1 - ease(phase(p, 0.75, 0.84))),
  };
}
