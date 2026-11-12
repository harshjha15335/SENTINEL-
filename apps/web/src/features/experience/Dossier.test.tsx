import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { DemoDossier } from "./Dossier";

describe("interactive payment dossier", () => {
  it("lets users switch authored examples and inspect the timeline in the inline story", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/intro"]}>
        <DemoDossier embedded />
      </MemoryRouter>,
    );

    const dossier = screen.getByRole("article", { name: "Payment dossier" });
    expect(dossier).toHaveTextContent("DEMO-0148");

    await user.click(screen.getByRole("button", { name: /Established pattern/i }));
    expect(dossier).toHaveTextContent("DEMO-0149");
    expect(screen.getByRole("button", { name: /Established pattern/i })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "timeline 02" }));
    expect(screen.getByRole("heading", { name: "Event timeline" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "overview 01" }));
    expect(screen.getByText("THE PAYMENT, IN DETAIL")).toBeInTheDocument();
  });
});
