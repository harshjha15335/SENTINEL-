import { screen } from "@testing-library/react";

import type { ModelCard } from "@/lib/api";
import { renderWithProviders } from "@/test/utils";

import { CapacityWarning } from "./CapacityWarning";

const card = (exceeded: boolean) =>
  ({
    review_capacity: {
      capacity_share: 0.08,
      test_flag_rate: exceeded ? 0.0939 : 0.07,
      exceeded,
      excess_share: exceeded ? 0.0139 : 0,
      policy_mode: "SHADOW",
      message: "The threshold was not re-tuned on test data; the policy stays in shadow mode.",
    },
  }) as unknown as ModelCard;

describe("CapacityWarning", () => {
  it("states the recorded flag rate against the planned capacity", () => {
    renderWithProviders(<CapacityWarning card={card(true)} />);
    expect(screen.getByRole("note", { name: "Review capacity warning" })).toHaveTextContent("9.4% flagged vs 8.0% planned");
    expect(screen.getByText(/not re-tuned on test data/)).toBeInTheDocument();
  });

  it("renders nothing within capacity", () => {
    renderWithProviders(<CapacityWarning card={card(false)} />);
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});
