import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/features/auth/session", () => ({
  useMe: () => ({
    isPending: false,
    isError: false,
    data: {
      email: "admin@northwind.example",
      role: "ADMIN",
      merchant: { name: "Northwind Supply Co. (sandbox)", environment: "DEMO" },
    },
  }),
  useLogout: () => ({ mutate: vi.fn(), isPending: false, isError: false }),
}));
vi.mock("./AppNavigation", () => ({ AppNavigation: () => null }));
vi.mock("./WorkspaceFonts", () => ({ WorkspaceFonts: () => null }));

import { AppShell } from "./AppShell";

describe("AppShell account banner removal", () => {
  it("renders navigation and the profile menu without the redundant merchant/gateway strip", () => {
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/app" element={<p>Command Center loaded</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Command Center loaded")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByText("admin@northwind.example")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Workspace account" })).not.toBeInTheDocument();
    expect(screen.queryByText("Demo dataset · offline gateway")).not.toBeInTheDocument();
    expect(screen.queryByText("Northwind Supply Co. (sandbox)")).not.toBeInTheDocument();
  });
});
