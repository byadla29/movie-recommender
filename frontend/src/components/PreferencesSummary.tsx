import type { Preferences, UserServiceResult } from "@/lib/api/user-service";

/**
 * Shows the user's saved preferences, or a calm explanation of why we can't.
 * Presentational only: it receives a result and renders it (no fetching here).
 */
export function PreferencesSummary({ result }: { result: UserServiceResult<Preferences> }) {
  if (result.ok) {
    const prefs = result.data;
    const languages = [...prefs.languages].sort((a, b) => a.rank - b.rank).map((l) => l.code);
    return (
      <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2">
        <dt className="font-medium">Country</dt>
        <dd>{prefs.country_code}</dd>
        <dt className="font-medium">Region</dt>
        <dd>{prefs.region_code ?? "Not set"}</dd>
        <dt className="font-medium">Languages</dt>
        <dd>{languages.join(", ")}</dd>
        <dt className="font-medium">Genres</dt>
        <dd>{prefs.genres.length > 0 ? prefs.genres.join(", ") : "None chosen"}</dd>
      </dl>
    );
  }

  const messages: Record<typeof result.reason, string> = {
    not_found: "You haven't chosen your region, languages and genres yet. Onboarding is coming next.",
    unauthorized: "We couldn't confirm your sign-in with our servers. Please sign out and sign in again.",
    unavailable: "Your preferences are temporarily unavailable. Please try again in a moment.",
    invalid: "Something about your saved preferences looks wrong. Please try again.",
    error: "Something went wrong while loading your preferences. Please try again.",
  };
  const isProblem = result.reason !== "not_found";
  return (
    <p role={isProblem ? "alert" : "status"} className="mt-4 text-zinc-700 dark:text-zinc-300">
      {messages[result.reason]}
    </p>
  );
}
