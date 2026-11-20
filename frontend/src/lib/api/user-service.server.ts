import "server-only";

import { auth } from "@clerk/nextjs/server";

import { getServiceUrls } from "@/lib/config";

import { getMyPreferences, type Preferences, type UserServiceResult } from "./user-service";

/**
 * Call user-service as the signed-in user. `server-only` makes the build fail if this file
 * is ever imported into browser code, so the token can't leak to the client by accident.
 */
async function currentUserToken(): Promise<string | null> {
  // Signed out → redirect to sign-in (nothing after this line runs).
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

export async function getMyPreferencesAsCurrentUser(): Promise<UserServiceResult<Preferences>> {
  const token = await currentUserToken();
  if (!token) return { ok: false, reason: "unauthorized", status: null };
  const result = await getMyPreferences(getServiceUrls()["user-service"], token);
  if (!(result.ok || result.reason === "not_found")) logFailure("get_preferences", result);
  return result;
}
