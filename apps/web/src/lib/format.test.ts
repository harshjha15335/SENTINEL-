import { formatMoney, humanize, shortId } from "./format";

describe("format", () => {
  it("formats minor units without floating-point drift", () => {
    expect(formatMoney(1999, "USD")).toBe("$19.99");
    expect(formatMoney(120000, "USD")).toBe("$1,200.00");
    expect(formatMoney(1200, "JPY")).toBe("¥1,200");
  });
  it("humanizes enum values", () => {
    expect(humanize("CAPTURE_PENDING")).toBe("Capture pending");
  });
  it("shortens long ids only", () => {
    expect(shortId("5O190127TN364715T")).toBe("5O190127…");
    expect(shortId("ABC")).toBe("ABC");
    expect(shortId(null)).toBe("—");
  });
});
