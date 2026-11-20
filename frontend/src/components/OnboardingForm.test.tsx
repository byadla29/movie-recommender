import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_VALUES, type OnboardingState, type OnboardingValues } from "@/lib/onboarding";

import { OnboardingForm } from "./OnboardingForm";

afterEach(cleanup);

const noop = async (previous: OnboardingState) => previous;

function renderForm(values: OnboardingValues = EMPTY_VALUES, action = noop) {
  return render(<OnboardingForm action={action} initialValues={values} isEditing={false} />);
}

describe("OnboardingForm", () => {
  it("labels every control so screen readers can name it", () => {
    renderForm();

    expect(screen.getByLabelText(/^Country/)).toBeDefined();
    expect(screen.getByLabelText(/^State or region/)).toBeDefined();
    expect(screen.getByLabelText(/^1st choice/)).toBeDefined();
    expect(screen.getByLabelText(/^5th choice/)).toBeDefined();
    expect(screen.getByLabelText("Thriller")).toBeDefined();
    expect(screen.getByLabelText(/Use my activity/)).toBeDefined();
  });

  it("has tracking switched OFF by default", () => {
    renderForm();

    expect((screen.getByLabelText(/Use my activity/) as HTMLInputElement).checked).toBe(false);
  });

  it("prefills saved choices when editing", () => {
    renderForm({ country_code: "IN", region_code: "IN-AP", languages: ["te", "en", "", "", ""], genres: ["drama"], tracking: true });

    expect((screen.getByLabelText(/^Country/) as HTMLSelectElement).value).toBe("IN");
    expect((screen.getByLabelText(/^State or region/) as HTMLSelectElement).value).toBe("IN-AP");
    expect((screen.getByLabelText(/^2nd choice/) as HTMLSelectElement).value).toBe("en");
    expect((screen.getByLabelText("Drama") as HTMLInputElement).checked).toBe(true);
    expect((screen.getByLabelText(/Use my activity/) as HTMLInputElement).checked).toBe(true);
  });

  it("shows errors from the action next to the field and in a summary", async () => {
    const action = vi.fn(async (previous: OnboardingState): Promise<OnboardingState> => ({
      values: { ...previous.values, languages: ["te", "te", "", "", ""] },
      errors: { languages: "Each language can only be chosen once." },
      submission: previous.submission + 1,
    }));
    renderForm({ ...EMPTY_VALUES, country_code: "IN", languages: ["te", "te", "", "", ""] }, action);

    fireEvent.click(screen.getByRole("button", { name: "Save and continue" }));

    const summary = await screen.findByRole("alert");
    expect(summary.textContent).toMatch(/Languages: Each language can only be chosen once/);
    await waitFor(() =>
      expect(screen.getByLabelText(/^1st choice/).getAttribute("aria-invalid")).toBe("true"),
    );
    // The user's choices survive the error.
    expect((screen.getByLabelText(/^2nd choice/) as HTMLSelectElement).value).toBe("te");
    expect(action).toHaveBeenCalledOnce();
  });
});
