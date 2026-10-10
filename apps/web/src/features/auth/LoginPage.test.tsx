import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { mockApi, renderWithProviders } from "@/test/utils";

import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("validates before calling the API", async () => {
    const calls = mockApi([{ path: "/api/v1/me", status: 401, body: { error: { code: "unauthenticated", message: "Sign in required" } } }]);
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: "/login" });
    await user.click(await screen.findByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(screen.getByLabelText("Work email")).toHaveAttribute("aria-invalid", "true");
    expect(calls.some((c) => c.url.endsWith("/auth/login"))).toBe(false);
  });

  it("shows the server's rejection", async () => {
    mockApi([
      { path: "/api/v1/me", status: 401, body: { error: { code: "unauthenticated", message: "Sign in required" } } },
      { method: "POST", path: "/api/v1/auth/login", status: 401, body: { error: { code: "unauthenticated", message: "Email or password is incorrect" } } },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: "/login" });
    await user.type(await screen.findByLabelText("Work email"), "a@b.example");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect");
  });
});
