import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const markIntroComplete = vi.hoisted(() => vi.fn());
vi.mock("./introSession", () => ({ markIntroComplete }));

import { WorkspaceEntryLink } from "./WorkspaceEntryLink";

afterEach(() => {
  vi.useRealTimers();
  markIntroComplete.mockClear();
});

describe("WorkspaceEntryLink", () => {
  it("shows a wallet transition before entering an authenticated workspace", () => {
    vi.useFakeTimers();
    render(
      <MemoryRouter initialEntries={["/intro"]}>
        <Routes>
          <Route
            path="/intro"
            element={
              <WorkspaceEntryLink to="/app" animated className="v2-button">
                Enter workspace
              </WorkspaceEntryLink>
            }
          />
          <Route path="/app" element={<p>Workspace ready</p>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("link", { name: "Enter workspace" }));
    expect(markIntroComplete).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status", { name: "Opening your workspace" })).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByText("Workspace ready")).toBeInTheDocument();
  });

  it("does not intercept illustrative public demo links", () => {
    render(
      <MemoryRouter initialEntries={["/intro"]}>
        <Routes>
          <Route path="/intro" element={
            <WorkspaceEntryLink to="/demo-payment" animated={false} className="v2-button">Explore demo</WorkspaceEntryLink>
          } />
          <Route path="/demo-payment" element={<p>Public demo</p>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("link", { name: "Explore demo" }));
    expect(screen.getByText("Public demo")).toBeInTheDocument();
    expect(markIntroComplete).not.toHaveBeenCalled();
  });
});
