import { describe, expect, it } from "vitest";

import { COUNTRY_OPTIONS, GENRE_OPTIONS, LANGUAGE_OPTIONS, labelFor, REGIONS_BY_COUNTRY } from "./vocab";

describe("vocab", () => {
  it("loads every choice from the contract copies", () => {
    expect(LANGUAGE_OPTIONS).toHaveLength(22);
    expect(GENRE_OPTIONS).toHaveLength(18);
    expect(COUNTRY_OPTIONS).toHaveLength(7);
    expect(REGIONS_BY_COUNTRY.IN).toHaveLength(36);
    expect(REGIONS_BY_COUNTRY.US).toBeUndefined(); // no listed regions → no region choices
  });

  it("shows languages in English and in their own script", () => {
    expect(labelFor("te")).toBe("Telugu (తెలుగు)");
    expect(labelFor("en")).toBe("English"); // not "English (English)"
  });

  it("names regions, countries and genres, and falls back to the code", () => {
    expect(labelFor("IN-AP")).toBe("Andhra Pradesh");
    expect(labelFor("IN")).toBe("India");
    expect(labelFor("science-fiction")).toBe("Science Fiction");
    expect(labelFor("zz-unknown")).toBe("zz-unknown");
  });

  it("sorts choices alphabetically by name", () => {
    const labels = LANGUAGE_OPTIONS.map((o) => o.label);
    expect(labels).toEqual([...labels].sort((a, b) => a.localeCompare(b, "en")));
  });
});
