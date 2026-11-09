import { describe, expect, it } from "vitest";
import { placement, transport } from "./scene";
describe("physical evidence transport", () => {
  it("does not transport tape before activation and stops at the end", () => {
    expect(transport(0).distance).toBe(0);
    expect(transport(0.14).distance).toBe(0);
    expect(transport(1).distance).toBe(2600);
    expect(transport(2)).toEqual(transport(1));
  });
  it("conserves wound cross-section while supply decreases and take-up grows", () => {
    const start = transport(0.14),
      end = transport(0.84);
    expect(end.supply).toBeLessThan(start.supply);
    expect(end.takeup).toBeGreaterThan(start.takeup);
    for (const p of [0.2, 0.4, 0.6, 0.8]) {
      const t = transport(p);
      expect(t.supply ** 2 + t.takeup ** 2).toBeCloseTo(92 ** 2 + 48 ** 2, 7);
    }
  });
  it("converts linear tape distance into angular travel at the current radius", () => {
    const a = transport(0.5 - 1e-5),
      b = transport(0.5 + 1e-5),
      mid = transport(0.5);
    const ds = b.distance - a.distance;
    expect((-(b.supplyAngle - a.supplyAngle) * Math.PI) / 180 / ds).toBeCloseTo(
      1 / mid.supply,
      6,
    );
    expect((-(b.takeupAngle - a.takeupAngle) * Math.PI) / 180 / ds).toBeCloseTo(
      1 / mid.takeup,
      6,
    );
  });
  it("keeps the object prominent at entry and reaches the receded placement at completion", () => {
    expect(placement(0).scale).toBe(1);
    expect(placement(1).scale).toBe(0.18);
    expect(placement(1).y).toBe(-180);
    expect(placement(0.4).exitX).toBeGreaterThan(0);
  });
});
