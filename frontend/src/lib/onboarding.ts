/**
 * Onboarding form logic, as plain functions (no React, no HTTP), so it is easy to test.
 *
 * Two layers of checking:
 * - here, quick friendly checks so people get feedback fast;
 * - user-service, the real authority, which checks everything again (never trust the form).
 */
import type { Consent, FieldError, Preferences, PreferencesInput } from "@/lib/api/user-service";
import { REGIONS_BY_COUNTRY } from "@/lib/vocab";

export const LANGUAGE_SLOTS = 5; // the API allows up to 10; five ordered choices keep the form short
export const MAX_GENRES = 5;
export const TRACKING_PURPOSE = "personalization_tracking";

export type OnboardingField = "country_code" | "region_code" | "languages" | "genres" | "tracking" | "form";
export type FieldErrors = Partial<Record<OnboardingField, string>>;

export interface OnboardingValues {
  country_code: string; // "" = not chosen
  region_code: string; // "" = none
  languages: string[]; // exactly LANGUAGE_SLOTS entries, "" = empty slot
  genres: string[];
  tracking: boolean;
}

export interface OnboardingState {
  values: OnboardingValues;
  errors: FieldErrors;
  /** Increases on every submit so the form re-mounts with the returned values. */
  submission: number;
}

export const EMPTY_VALUES: OnboardingValues = {
  country_code: "",
  region_code: "",
  languages: Array<string>(LANGUAGE_SLOTS).fill(""),
  genres: [],
  tracking: false, // privacy by default
};

const text = (value: FormDataEntryValue | null) => (typeof value === "string" ? value.trim() : "");

export function readOnboardingForm(formData: FormData): OnboardingValues {
  return {
    country_code: text(formData.get("country_code")),
    region_code: text(formData.get("region_code")),
    languages: Array.from({ length: LANGUAGE_SLOTS }, (_, i) => text(formData.get(`language_${i + 1}`))),
    genres: formData.getAll("genres").map(text).filter(Boolean),
    tracking: formData.get("tracking") === "on", // an unticked checkbox sends nothing at all
  };
}

/** The chosen languages in order, skipping empty slots (1st, 3rd → ranks 1 and 2). */
export function chosenLanguages(values: OnboardingValues): string[] {
  return values.languages.filter(Boolean);
}

export function checkOnboarding(values: OnboardingValues): FieldErrors {
  const errors: FieldErrors = {};
  if (!values.country_code) errors.country_code = "Choose your country.";
  if (values.region_code) {
    const regions = REGIONS_BY_COUNTRY[values.country_code] ?? [];
    if (!regions.some((r) => r.code === values.region_code)) {
      errors.region_code = "This region isn't in the country you chose.";
    }
  }
  const languages = chosenLanguages(values);
  if (languages.length === 0) errors.languages = "Choose at least one language.";
  else if (new Set(languages).size !== languages.length) errors.languages = "Each language can only be chosen once.";
  if (values.genres.length > MAX_GENRES) errors.genres = `Choose at most ${MAX_GENRES} genres.`;
  return errors;
}

export function toPreferencesInput(values: OnboardingValues): PreferencesInput {
  return {
    country_code: values.country_code,
    region_code: values.region_code || null,
    languages: chosenLanguages(values),
    genres: values.genres,
  };
}

const SERVER_FIELD_MESSAGES: Record<string, string> = {
  country_code: "This country isn't supported.",
  region_code: "This region isn't in the country you chose.",
  languages: "Please check your languages: each must be supported and chosen once.",
  genres: "Please check your genres: each must be supported, at most 5.",
};

/** Turn user-service's 422 details (loc = ["body", field, index?]) into per-field messages. */
export function fieldErrorsFromServer(errors: FieldError[]): FieldErrors {
  const result: FieldErrors = {};
  for (const error of errors) {
    const field = error.loc[1];
    if (typeof field === "string" && field in SERVER_FIELD_MESSAGES) {
      result[field as OnboardingField] = SERVER_FIELD_MESSAGES[field];
    } else {
      result.form = "Some of your choices couldn't be saved. Please review them and try again.";
    }
  }
  return result;
}

/** Prefill the form from what is already saved (editing), or start empty (first time). */
export function valuesFromSaved(preferences: Preferences | null, consents: Consent[]): OnboardingValues {
  const tracking = consents.find((c) => c.purpose === TRACKING_PURPOSE)?.granted ?? false;
  if (!preferences) return { ...EMPTY_VALUES, tracking };
  const ordered = [...preferences.languages].sort((a, b) => a.rank - b.rank).map((l) => l.code);
  return {
    country_code: preferences.country_code,
    region_code: preferences.region_code ?? "",
    languages: Array.from({ length: LANGUAGE_SLOTS }, (_, i) => ordered[i] ?? ""),
    genres: preferences.genres,
    tracking,
  };
}
