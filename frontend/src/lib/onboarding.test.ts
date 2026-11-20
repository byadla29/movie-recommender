import { describe, expect, it } from "vitest";

import {
  checkOnboarding,
  EMPTY_VALUES,
  fieldErrorsFromServer,
  type OnboardingValues,
  readOnboardingForm,
  toPreferencesInput,
  valuesFromSaved,
} from "./onboarding";

function form(entries: [string, string][]): FormData {
  const data = new FormData();
  for (const [key, value] of entries) data.append(key, value);
  return data;
}

const VALID: OnboardingValues = {
  country_code: "IN",
  region_code: "IN-AP",
  languages: ["te", "en", "", "", ""],
  genres: ["thriller"],
  tracking: false,
};

describe("readOnboardingForm", () => {
  it("reads every field, keeping language slots in order", () => {
    const values = readOnboardingForm(
      form([
        ["country_code", "IN"],
        ["region_code", ""],
        ["language_1", "te"],
        ["language_3", "hi"],
        ["genres", "drama"],
        ["genres", "thriller"],
        ["tracking", "on"],
      ]),
    );

    expect(values).toEqual({
      country_code: "IN",
      region_code: "",
      languages: ["te", "", "hi", "", ""],
      genres: ["drama", "thriller"],
      tracking: true,
    });
  });

  it("treats a missing checkbox as 'no' (browsers send nothing for unticked boxes)", () => {
    expect(readOnboardingForm(form([["country_code", "IN"]])).tracking).toBe(false);
  });
});

describe("checkOnboarding", () => {
  it("accepts valid choices", () => {
    expect(checkOnboarding(VALID)).toEqual({});
  });

  it.each<[string, Partial<OnboardingValues>, string]>([
    ["no country", { country_code: "", region_code: "" }, "country_code"],
    ["region of another country", { country_code: "US", region_code: "IN-AP" }, "region_code"],
    ["no language", { languages: ["", "", "", "", ""] }, "languages"],
    ["the same language twice", { languages: ["te", "te", "", "", ""] }, "languages"],
    ["six genres", { genres: ["action", "comedy", "crime", "drama", "horror", "war"] }, "genres"],
  ])("flags %s", (_case, change, field) => {
    expect(Object.keys(checkOnboarding({ ...VALID, ...change }))).toEqual([field]);
  });
});

describe("toPreferencesInput", () => {
  it("compacts language slots into a ranked list and turns an empty region into null", () => {
    expect(toPreferencesInput({ ...VALID, region_code: "", languages: ["", "te", "", "en", ""] })).toEqual({
      country_code: "IN",
      region_code: null,
      languages: ["te", "en"],
      genres: ["thriller"],
    });
  });
});

describe("fieldErrorsFromServer", () => {
  it("maps user-service error locations to form fields", () => {
    const errors = fieldErrorsFromServer([
      { loc: ["body", "languages", 1], msg: "Not a supported value", type: "unknown_code" },
      { loc: ["body", "region_code"], msg: "x", type: "region_not_in_country" },
    ]);

    expect(Object.keys(errors).sort()).toEqual(["languages", "region_code"]);
  });

  it("falls back to a form-level message for anything unexpected", () => {
    expect(Object.keys(fieldErrorsFromServer([{ loc: ["body"], msg: "x", type: "y" }]))).toEqual(["form"]);
  });
});

describe("valuesFromSaved", () => {
  it("starts empty with tracking OFF for a new user", () => {
    expect(valuesFromSaved(null, [])).toEqual(EMPTY_VALUES);
    expect(EMPTY_VALUES.tracking).toBe(false);
  });

  it("prefills saved choices, languages in rank order", () => {
    const values = valuesFromSaved(
      {
        country_code: "IN",
        region_code: null,
        languages: [
          { code: "en", rank: 2 },
          { code: "te", rank: 1 },
        ],
        genres: ["drama"],
        onboarded_at: "",
        updated_at: "",
      },
      [{ purpose: "personalization_tracking", granted: true, updated_at: "2026-11-20T00:00:00Z" }],
    );

    expect(values).toEqual({
      country_code: "IN",
      region_code: "",
      languages: ["te", "en", "", "", ""],
      genres: ["drama"],
      tracking: true,
    });
  });
});
