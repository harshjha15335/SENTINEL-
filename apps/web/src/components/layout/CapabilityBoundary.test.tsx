import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, test, expect } from "vitest";
vi.mock("@/lib/staticDemo", () => ({ STATIC_DEMO: true }));
import { CapabilityBoundary } from "./CapabilityBoundary";
import { CAPABILITIES } from "@/lib/capabilities";

test("static service boundaries never mount operational children and provide return links", () => {
  const mount = vi.fn();
  function Service() {
    mount();
    return <p>Service mounted</p>;
  }
  render(
    <MemoryRouter>
      {Object.entries(CAPABILITIES)
        .filter(([, value]) => !value.static)
        .map(([key]) => (
          <CapabilityBoundary
            key={key}
            capability={key as keyof typeof CAPABILITIES}
          >
            <Service />
          </CapabilityBoundary>
        ))}
    </MemoryRouter>,
  );
  expect(mount).not.toHaveBeenCalled();
  expect(screen.getAllByText(/Requires the full application/)).toHaveLength(12);
  expect(
    screen.getAllByRole("link", { name: "Browse recorded payments" }),
  ).toHaveLength(12);
});

test("recorded case browsing remains available", () => {
  render(
    <CapabilityBoundary capability="cases">
      <p>Recorded case facts</p>
    </CapabilityBoundary>,
  );
  expect(screen.getByText("Recorded case facts")).toBeVisible();
});
