import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const logoutMutate = vi.hoisted(() => vi.fn());
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
  useLogout: () => ({ mutate: logoutMutate, isPending: false, isError: false }),
}));
vi.mock("./AppNavigation", () => ({ AppNavigation: () => null }));
vi.mock("./WorkspaceFonts", () => ({ WorkspaceFonts: () => null }));

import { AppShell } from "./AppShell";

function mountWorkspace() {
  return render(
    <MemoryRouter initialEntries={["/app"]}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/app" element={<p>Command Center loaded</p>} />
          <Route path="/app/settings" element={<p>Integration settings loaded</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("AppShell account menu", () => {
  it("shows working navigation and a non-overlaying, collapsible account menu", () => {
    mountWorkspace();
    expect(screen.getByText("Command Center loaded")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.queryByText("Demo dataset · offline gateway")).not.toBeInTheDocument();
    expect(screen.queryByText("Northwind Supply Co. (sandbox)")).not.toBeInTheDocument();
    const trigger = screen.getByRole("button", { name: "Open account menu" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("admin@northwind.example")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: /Account & integrations/i }));
    expect(screen.getByText("Integration settings loaded")).toBeInTheDocument();
  });

  it("invokes real logout mutation instead of an inert menu button", () => {
    logoutMutate.mockClear();
    mountWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Open account menu" }));
    fireEvent.click(screen.getByRole("button", { name: /Sign out/i }));
    expect(logoutMutate).toHaveBeenCalledTimes(1);
  });
});
