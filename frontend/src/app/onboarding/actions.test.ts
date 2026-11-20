import { beforeEach, describe, expect, it, vi } from "vitest";

import { EMPTY_VALUES, type OnboardingState } from "@/lib/onboarding";

// The action's collaborators are replaced with fakes: we test its decisions, not the network.
const api = vi.hoisted(() => ({
  putMyPreferencesAsCurrentUser: vi.fn(),
  putMyConsentAsCurrentUser: vi.fn(),
}));
vi.mock("@/lib/api/user-service.server", () => api);

const redirect = vi.hoisted(() =>
  vi.fn((path: string) => {
    throw new Error(`REDIRECT:${path}`); // like Next.js, redirect() stops the function
  }),
);
vi.mock("next/navigation", () => ({ redirect }));

const { saveOnboarding } = await import("./actions");

const START: OnboardingState = { values: EMPTY_VALUES, errors: {}, submission: 0 };

function form(entries: [string, string][]): FormData {
  const data = new FormData();
  for (const [key, value] of entries) data.append(key, value);
  return data;
}

const VALID_FORM: [string, string][] = [
  ["country_code", "IN"],
  ["region_code", "IN-AP"],
  ["language_1", "te"],
  ["language_2", "en"],
  ["genres", "thriller"],
];

describe("saveOnboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.putMyPreferencesAsCurrentUser.mockResolvedValue({ ok: true, data: {} });
    api.putMyConsentAsCurrentUser.mockResolvedValue({ ok: true, data: {} });
  });

  it("saves preferences, then consent, then goes to /home", async () => {
    await expect(saveOnboarding(START, form([...VALID_FORM, ["tracking", "on"]]))).rejects.toThrow(
      "REDIRECT:/home",
    );

    expect(api.putMyPreferencesAsCurrentUser).toHaveBeenCalledWith({
      country_code: "IN",
      region_code: "IN-AP",
      languages: ["te", "en"],
      genres: ["thriller"],
    });
    expect(api.putMyConsentAsCurrentUser).toHaveBeenCalledWith("personalization_tracking", true);
  });

  it("records an explicit 'no' when the consent box is left unticked", async () => {
    await expect(saveOnboarding(START, form(VALID_FORM))).rejects.toThrow("REDIRECT:/home");

    expect(api.putMyConsentAsCurrentUser).toHaveBeenCalledWith("personalization_tracking", false);
  });

  it("stops before calling user-service when quick checks fail, keeping the choices", async () => {
    const state = await saveOnboarding(START, form([["language_1", "te"]]));

    expect(api.putMyPreferencesAsCurrentUser).not.toHaveBeenCalled();
    expect(state.errors.country_code).toBeDefined();
    expect(state.values.languages[0]).toBe("te");
    expect(state.submission).toBe(1);
  });

  it("shows user-service's validation errors next to the right fields", async () => {
    api.putMyPreferencesAsCurrentUser.mockResolvedValue({
      ok: false,
      reason: "invalid",
      status: 422,
      errors: [{ loc: ["body", "genres", 0], msg: "Not a supported value", type: "unknown_code" }],
    });

    const state = await saveOnboarding(START, form(VALID_FORM));

    expect(Object.keys(state.errors)).toEqual(["genres"]);
    expect(api.putMyConsentAsCurrentUser).not.toHaveBeenCalled();
  });

  it("explains an outage calmly and keeps everything the user chose", async () => {
    api.putMyPreferencesAsCurrentUser.mockResolvedValue({ ok: false, reason: "unavailable", status: 503 });

    const state = await saveOnboarding(START, form(VALID_FORM));

    expect(state.errors.form).toMatch(/try again/);
    expect(state.values.country_code).toBe("IN");
  });

  it("says so if preferences saved but the consent answer didn't", async () => {
    api.putMyConsentAsCurrentUser.mockResolvedValue({ ok: false, reason: "unavailable", status: null });

    const state = await saveOnboarding(START, form(VALID_FORM));

    expect(state.errors.tracking).toMatch(/preferences were saved/);
    expect(redirect).not.toHaveBeenCalled();
  });
});
