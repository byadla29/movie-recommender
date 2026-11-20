"use client";

import { useActionState } from "react";

import {
  LANGUAGE_SLOTS,
  MAX_GENRES,
  type OnboardingField,
  type OnboardingState,
  type OnboardingValues,
} from "@/lib/onboarding";
import { COUNTRY_OPTIONS, GENRE_OPTIONS, LANGUAGE_OPTIONS, REGIONS_BY_COUNTRY } from "@/lib/vocab";

type SaveAction = (previous: OnboardingState, formData: FormData) => Promise<OnboardingState>;

const ORDINALS = ["1st", "2nd", "3rd", "4th", "5th"];

const FIELD_ANCHORS: Record<OnboardingField, string> = {
  country_code: "country_code",
  region_code: "region_code",
  languages: "language_1",
  genres: "genres",
  tracking: "tracking",
  form: "onboarding-form",
};

const FIELD_NAMES: Record<OnboardingField, string> = {
  country_code: "Country",
  region_code: "Region",
  languages: "Languages",
  genres: "Genres",
  tracking: "Personalization",
  form: "Saving",
};

const control =
  "mt-1 block w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-zinc-900 focus-visible:outline-2 focus-visible:outline-offset-2 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100";

/**
 * The onboarding form: four short sections on one page.
 *
 * - Works without JavaScript: it is a real <form> posting to a Server Action.
 * - The action is passed in as a prop, so tests can use a fake one.
 * - After each submit the form re-mounts (`key`) with the values the action sent back,
 *   so nothing the user chose disappears when there is an error.
 */
export function OnboardingForm({
  action,
  initialValues,
  isEditing,
}: {
  action: SaveAction;
  initialValues: OnboardingValues;
  isEditing: boolean;
}) {
  const [state, formAction, pending] = useActionState(action, {
    values: initialValues,
    errors: {},
    submission: 0,
  });
  const { values, errors } = state;
  const errorEntries = Object.entries(errors) as [OnboardingField, string][];

  const describedBy = (field: OnboardingField, hint?: string) =>
    [hint, errors[field] ? `${field}-error` : undefined].filter(Boolean).join(" ") || undefined;

  const fieldError = (field: OnboardingField) =>
    errors[field] ? (
      <p id={`${field}-error`} className="mt-1 text-sm font-medium text-red-700 dark:text-red-400">
        {errors[field]}
      </p>
    ) : null;

  return (
    <form key={state.submission} id="onboarding-form" action={formAction} className="mt-8 space-y-10">
      {errorEntries.length > 0 && (
        <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950">
          <h2 className="font-semibold text-red-800 dark:text-red-300">Please check your choices</h2>
          <ul className="mt-2 list-disc pl-5 text-sm text-red-800 dark:text-red-300">
            {errorEntries.map(([field, message]) => (
              <li key={field}>
                <a href={`#${FIELD_ANCHORS[field]}`} className="underline">
                  {FIELD_NAMES[field]}: {message}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <fieldset>
        <legend className="text-lg font-semibold">1. Where are you?</legend>
        <p id="location-hint" className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Used for &ldquo;popular in your region&rdquo; rows. It never decides your languages for you.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="country_code" className="font-medium">
              Country <span className="text-sm font-normal">(required)</span>
            </label>
            <select
              id="country_code"
              name="country_code"
              required
              defaultValue={values.country_code}
              aria-invalid={Boolean(errors.country_code)}
              aria-describedby={describedBy("country_code", "location-hint")}
              className={control}
            >
              <option value="">Choose a country</option>
              {COUNTRY_OPTIONS.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
            {fieldError("country_code")}
          </div>
          <div>
            <label htmlFor="region_code" className="font-medium">
              State or region <span className="text-sm font-normal">(optional)</span>
            </label>
            <select
              id="region_code"
              name="region_code"
              defaultValue={values.region_code}
              aria-invalid={Boolean(errors.region_code)}
              aria-describedby={describedBy("region_code")}
              className={control}
            >
              <option value="">Prefer not to say</option>
              {Object.entries(REGIONS_BY_COUNTRY).map(([country, regions]) => (
                <optgroup key={country} label={COUNTRY_OPTIONS.find((c) => c.code === country)?.label ?? country}>
                  {regions.map((r) => (
                    <option key={r.code} value={r.code}>
                      {r.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            {fieldError("region_code")}
          </div>
        </div>
      </fieldset>

      <fieldset aria-describedby={describedBy("languages", "languages-hint")}>
        <legend className="text-lg font-semibold">2. Languages you watch in</legend>
        <p id="languages-hint" className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          In order of preference. Your 1st choice is required; leave the others empty if you like.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {Array.from({ length: LANGUAGE_SLOTS }, (_, i) => (
            <div key={i}>
              <label htmlFor={`language_${i + 1}`} className="font-medium">
                {ORDINALS[i]} choice{i === 0 && <span className="text-sm font-normal"> (required)</span>}
              </label>
              <select
                id={`language_${i + 1}`}
                name={`language_${i + 1}`}
                required={i === 0}
                defaultValue={values.languages[i] ?? ""}
                aria-invalid={Boolean(errors.languages)}
                className={control}
              >
                <option value="">{i === 0 ? "Choose a language" : "None"}</option>
                {LANGUAGE_OPTIONS.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
        {fieldError("languages")}
      </fieldset>

      <fieldset id="genres" aria-describedby={describedBy("genres", "genres-hint")}>
        <legend className="text-lg font-semibold">3. Genres you enjoy</legend>
        <p id="genres-hint" className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Optional, up to {MAX_GENRES}.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
          {GENRE_OPTIONS.map((g) => (
            <label key={g.code} className="flex items-center gap-2">
              <input
                type="checkbox"
                name="genres"
                value={g.code}
                defaultChecked={values.genres.includes(g.code)}
                className="size-4"
              />
              {g.label}
            </label>
          ))}
        </div>
        {fieldError("genres")}
      </fieldset>

      <fieldset>
        <legend className="text-lg font-semibold">4. Personalization</legend>
        <div className="mt-4 flex items-start gap-3">
          <input
            id="tracking"
            type="checkbox"
            name="tracking"
            defaultChecked={values.tracking}
            aria-describedby={describedBy("tracking", "tracking-hint")}
            className="mt-1 size-4"
          />
          <div>
            <label htmlFor="tracking" className="font-medium">
              Use my activity on this site to improve recommendations
            </label>
            <p id="tracking-hint" className="text-sm text-zinc-600 dark:text-zinc-400">
              If you allow it, we record which movies you view, click, like or skip here. It&apos;s off
              unless you tick it, and you can change it any time in Settings.
            </p>
            {fieldError("tracking")}
          </div>
        </div>
      </fieldset>

      {errors.form && (
        <p role="alert" className="font-medium text-red-700 dark:text-red-400">
          {errors.form}
        </p>
      )}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-zinc-900 px-5 py-2.5 font-medium text-white hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
      >
        {pending ? "Saving…" : isEditing ? "Save changes" : "Save and continue"}
      </button>
    </form>
  );
}
