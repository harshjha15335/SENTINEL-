import { describe, it, expect } from "vitest";
import { moneyScene } from "./money-scene";
describe("deterministic money journey", () => {
  it("keeps the wallet closed and receipt hidden initially", () => {
    const s = moneyScene(0);
    expect(s.open).toBe(0);
    expect(s.receipt.opacity).toBe(0);
  });
  it("opens progressively and isolates the same receipt before assembly", () => {
    expect(moneyScene(0.15).open).toBeGreaterThan(0);
    expect(moneyScene(0.24).open).toBe(1);
    expect(moneyScene(0.6).isolate).toBe(1);
    expect(moneyScene(0.65).receipt.opacity).toBe(1);
    expect(moneyScene(0.65).field).toBe(1);
  });
  it("settles at a fixed position independent of previous samples", () => {
    const s = moneyScene(0.5);
    moneyScene(0.9);
    expect(moneyScene(0.5)).toEqual(s);
    expect(moneyScene(-1)).toEqual(moneyScene(0));
    expect(moneyScene(2)).toEqual(moneyScene(1));
  });
  it("reaches the actual workspace and retires the illustration", () => {
    const s = moneyScene(1);
    expect(s.assemble).toBe(1);
    expect(s.receipt.opacity).toBe(0);
    expect(s.wallet.opacity).toBe(0);
    expect(s.stage).toBe(6);
  });
});
