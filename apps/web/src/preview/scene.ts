export const stageBoundaries = [0, 0.14, 0.3, 0.48, 0.66, 0.84] as const;
export const clamp = (n: number) => Math.max(0, Math.min(1, n));
export const mix = (a: number, b: number, p: number) => a + (b - a) * p;
export const segment = (p: number, start: number, end: number) =>
  clamp((p - start) / (end - start));
export const smooth = (p: number) => p * p * (3 - 2 * p);

/** Conserved wound cross-section and integrated angular travel for a uniform-thickness tape. */
export function transport(progress: number) {
  const advance = segment(progress, 0.14, 0.84);
  const distance = advance * 2600;
  const inner = 48,
    outer = 92,
    area = outer * outer - inner * inner;
  const supply = Math.sqrt(outer * outer - advance * area);
  const takeup = Math.sqrt(inner * inner + advance * area);
  return {
    advance,
    distance,
    supply,
    takeup,
    supplyAngle: (((-2 * 2600) / area) * (outer - supply) * 180) / Math.PI,
    takeupAngle: (((-2 * 2600) / area) * (takeup - inner) * 180) / Math.PI,
  };
}
const placements = [
  [0, 580, 140, 1, 0],
  [0.14, 580, 140, 1, 0],
  [0.3, 720, 20, 0.68, -8],
  [0.48, 830, -55, 0.49, -12],
  [0.66, 920, -100, 0.36, -17],
  [0.84, 1000, -145, 0.24, -21],
  [1, 1060, -180, 0.18, -25],
] as const;
export function placement(p: number) {
  const found = placements.findIndex(
    (k, j) =>
      j < placements.length - 1 &&
      p >= k[0] &&
      p < (placements[j + 1]?.[0] ?? 2),
  );
  const i = found >= 0 ? found : p <= 0 ? 0 : placements.length - 2;
  const a = placements[i] ?? placements[0],
    b = placements[i + 1] ?? placements[6];
  const t = smooth(segment(p, a[0], b[0]));
  const x = mix(a[1], b[1], t),
    y = mix(a[2], b[2], t),
    scale = mix(a[3], b[3], t),
    angle = mix(a[4], b[4], t);
  const theta = (angle * Math.PI) / 180;
  const dx = 763 - 410,
    dy = 380 - 280;
  return {
    x,
    y,
    scale,
    angle,
    exitX: x + scale * (410 + Math.cos(theta) * dx - Math.sin(theta) * dy),
    exitY: y + scale * (280 + Math.sin(theta) * dx + Math.cos(theta) * dy),
  };
}
/** One physical strip remains connected to the moving output port as it straightens into a dossier. */
export function evidencePath(p: number, exitX: number, exitY: number) {
  const t = smooth(segment(p, 0.63, 0.88));
  const loose = [
    [exitX + 110, exitY + 25],
    [1390, 290],
    [1190, 355],
    [1050, 500],
    [970, 200],
    [790, 380],
    [590, 610],
    [310, 330],
    [295, 535],
    [250, 790],
    [460, 790],
    [590, 690],
    [805, 535],
    [1040, 805],
    [1120, 610],
  ];
  const ordered = [
    [exitX + 90, exitY + 10],
    [1340, 180],
    [1140, 240],
    [1000, 280],
    [760, 275],
    [650, 340],
    [500, 420],
    [375, 420],
    [375, 470],
    [375, 540],
    [375, 625],
    [470, 650],
    [690, 705],
    [1000, 690],
    [1120, 610],
  ];
  const points = loose.map((point, i) =>
    point.map((value, j) => mix(value, ordered[i]?.[j] ?? value, t)),
  );
  let d = `M${exitX.toFixed(2)} ${exitY.toFixed(2)}`;
  for (let i = 0; i < points.length; i += 3)
    d += ` C${points
      .slice(i, i + 3)
      .map((pt) => pt.map((v) => v.toFixed(2)).join(" "))
      .join(" ")}`;
  return d;
}
