/**
 * Choices and display names for countries, regions, languages and genres.
 *
 * The JSON files in `src/vocab/` are copies of `contracts/vocab/` made by
 * `scripts/sync-vocab.sh` (CI fails if they drift). The frontend shows names; services store
 * and validate codes. Never edit the copies by hand.
 */
import genresFile from "@/vocab/genres.v1.json";
import languagesFile from "@/vocab/languages.v1.json";
import regionsFile from "@/vocab/regions.v1.json";

export interface Option {
  code: string;
  label: string;
}

const byLabel = (a: Option, b: Option) => a.label.localeCompare(b.label, "en");

/** "Telugu (తెలుగు)": the English name plus the name in the language itself. */
export const LANGUAGE_OPTIONS: Option[] = languagesFile.items
  .map((l) => ({ code: l.code, label: l.name === l.native_name ? l.name : `${l.name} (${l.native_name})` }))
  .sort(byLabel);

export const GENRE_OPTIONS: Option[] = genresFile.items.map((g) => ({ code: g.code, label: g.name })).sort(byLabel);

export const COUNTRY_OPTIONS: Option[] = regionsFile.items
  .map((c) => ({ code: c.code, label: c.name }))
  .sort(byLabel);

/** Only countries that have listed regions appear here (India in the launch set). */
export const REGIONS_BY_COUNTRY: Record<string, Option[]> = Object.fromEntries(
  regionsFile.items
    .filter((c) => c.regions.length > 0)
    .map((c) => [c.code, c.regions.map((r) => ({ code: r.code, label: r.name })).sort(byLabel)]),
);

const LABELS: Record<string, string> = Object.fromEntries(
  [...LANGUAGE_OPTIONS, ...GENRE_OPTIONS, ...COUNTRY_OPTIONS, ...Object.values(REGIONS_BY_COUNTRY).flat()].map(
    (o) => [o.code, o.label],
  ),
);

/** Display name for any code; falls back to the code itself if it's unknown here. */
export function labelFor(code: string): string {
  return LABELS[code] ?? code;
}
