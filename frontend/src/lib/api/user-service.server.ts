import "server-only";

import { auth } from "@clerk/nextjs/server";
import { connection } from "next/server";

import { getServiceUrls } from "@/lib/config";

import {
  type Consent,
  deleteMyAccountData,
  getMyConsents,
  getMyPreferences,
  type Preferences,
  type PreferencesInput,
  putMyConsent,
  putMyPreferences,
  type UserServiceResult,
} from "./user-service";

/**
 * Call user-service as the signed-in user. `server-only` makes the build fail if this file
 * is ever imported into browser code, so the token can't leak to the client by accident.
 *
 * Every function checks the session itself (auth.protect), so each one is safe to use from
 * a Server Action: an action is a public endpoint, whatever page its form appears on.
 */
async function currentUserToken(): Promise<string | null> {
  // Signed out → redirect to sign-in (pages) or 401 (Server Actions). Nothing after runs.
  const { getToken } = await auth.protect();
  // A short-lived (about a minute) Clerk session token for this user.
  return getToken();
}

function logFailure(operation: string, result: UserServiceResult<unknown>): void {
  if (result.ok) return;
  // Operational log for us: what failed and how. Never the token or the user's data.
  console.warn(
    JSON.stringify({ level: "warn", message: "user-service call failed", operation, reason: result.reason, status: result.status }),
  );
}

async function asCurrentUser<T>(
  operation: string,
  call: (baseUrl: string, token: string) => Promise<UserServiceResult<T>>,
  expected: ReadonlyArray<string> = [],
): Promise<UserServiceResult<T>> {
  const token = await currentUserToken();
  if (!token) return { ok: false, reason: "unauthorized", status: null };
  // Next.js may pre-render pages in the background (e.g. when a link to them is shown).
  // connection() stops that pre-render here, so the request id and the call to
  // user-service only ever happen for a real visit, never in a background pre-render.
  await connection();
  const result = await call(getServiceUrls()["user-service"], token);
  if (!result.ok && !expected.includes(result.reason)) logFailure(operation, result);
  return result;
}

export function getMyPreferencesAsCurrentUser(): Promise<UserServiceResult<Preferences>> {
  return asCurrentUser("get_preferences", getMyPreferences, ["not_found"]);
}

export function putMyPreferencesAsCurrentUser(body: PreferencesInput): Promise<UserServiceResult<Preferences>> {
  return asCurrentUser("put_preferences", (url, token) => putMyPreferences(url, token, body), ["invalid"]);
}

export function getMyConsentsAsCurrentUser(): Promise<UserServiceResult<{ consents: Consent[] }>> {
  return asCurrentUser("get_consents", getMyConsents);
}

export function putMyConsentAsCurrentUser(purpose: string, granted: boolean): Promise<UserServiceResult<Consent>> {
  return asCurrentUser("put_consent", (url, token) => putMyConsent(url, token, purpose, granted));
}

export function deleteMyAccountDataAsCurrentUser(): Promise<UserServiceResult<void>> {
  return asCurrentUser("delete_account_data", deleteMyAccountData);
}
