import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { FailureReason } from "@/lib/api/user-service";

import { PreferencesSummary } from "./PreferencesSummary";

afterEach(cleanup);

describe("PreferencesSummary", () => {
  it("lists saved preferences with languages in rank order", () => {
    render(
      <PreferencesSummary
        result={{
          ok: true,
          data: {
            country_code: "IN",
            region_code: null,
            languages: [
              { code: "en", rank: 2 },
              { code: "te", rank: 1 },
            ],
            genres: [],
            onboarded_at: "2026-11-20T10:00:00Z",
            updated_at: "2026-11-20T10:00:00Z",
          },
        }}
      />,
    );

    expect(screen.getByText("IN")).toBeDefined();
    expect(screen.getByText("te, en")).toBeDefined();
    expect(screen.getByText("Not set")).toBeDefined();
    expect(screen.getByText("None chosen")).toBeDefined();
  });

  it("explains 'not onboarded yet' as information, not an error", () => {
    render(<PreferencesSummary result={{ ok: false, reason: "not_found", status: 404 }} />);

    expect(screen.getByRole("status").textContent).toMatch(/haven't chosen/);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each<[FailureReason, RegExp]>([
    ["unauthorized", /sign out and sign in again/],
    ["unavailable", /temporarily unavailable/],
    ["error", /Something went wrong/],
  ])("shows a calm, actionable message for %s", (reason, message) => {
    render(<PreferencesSummary result={{ ok: false, reason, status: null }} />);

    expect(screen.getByRole("alert").textContent).toMatch(message);
  });
});
