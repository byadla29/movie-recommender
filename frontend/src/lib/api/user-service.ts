/**
 * Calls from the Next.js server (the BFF) to user-service, on behalf of the signed-in user.
 *
 * - The user's Clerk token travels as `Authorization: Bearer <token>`; user-service checks it
 *   itself (step 2.3). The token stays on our server: the browser never calls user-service.
 * - Every call has a timeout, so a slow service can't hang the page.
 * - Every outcome becomes a small, typed result the page can show calmly. Pages never see
 *   raw HTTP errors, and nothing here ever includes the token.
 *
 * This file takes the token and URL as inputs (easy to test with a fake fetch). The
 * server-only wrapper that gets them from Clerk lives in `user-service.server.ts`.
 */

export interface RankedLanguage {
  code: string;
  rank: number;
}

export interface Preferences {
  country_code: string;
  region_code: string | null;
  languages: RankedLanguage[];
  genres: string[];
  onboarded_at: string;
  updated_at: string;
}

export interface FieldError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** Why a call didn't succeed, in terms a page can act on. */
export type FailureReason =
  | "not_found" // 404: e.g. no preferences saved yet
  | "unauthorized" // 401: user-service didn't accept the token
  | "invalid" // 422: the data we sent broke a rule (see `errors`)
  | "unavailable" // 503, timeout or network error: try again later
  | "error"; // anything unexpected

export type UserServiceResult<T> =
  | { ok: true; data: T }
  | { ok: false; reason: FailureReason; status: number | null; errors?: FieldError[] };

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface CallOptions {
  method?: "GET" | "PUT" | "DELETE";
  body?: unknown;
  fetchImpl?: FetchLike;
  timeoutMs?: number;
  /** Extra attempts when the service is unavailable. Only for idempotent calls. */
  retries?: number;
  requestId?: string;
}

// docs/service-communication.md §2, call #1: 1500 ms covers user-service's first token check,
// which downloads the identity provider's public keys; later checks use its cached keys.
export const DEFAULT_TIMEOUT_MS = 1500;

export async function callUserService<T>(
  baseUrl: string,
  path: string,
  token: string,
  options: CallOptions = {},
): Promise<UserServiceResult<T>> {
  const { retries = 0, requestId = crypto.randomUUID(), ...rest } = options;
  // Same request ID on every attempt: the logs show one user action, tried N times.
  let result = await attempt<T>(baseUrl, path, token, { ...rest, requestId });
  for (let i = 0; i < retries && !result.ok && result.reason === "unavailable"; i++) {
    result = await attempt<T>(baseUrl, path, token, { ...rest, requestId });
  }
  return result;
}

async function attempt<T>(
  baseUrl: string,
  path: string,
  token: string,
  options: Omit<CallOptions, "retries"> & { requestId: string },
): Promise<UserServiceResult<T>> {
  const { method = "GET", body, fetchImpl = fetch, timeoutMs = DEFAULT_TIMEOUT_MS, requestId } = options;

  let response: Response;
  try {
    response = await fetchImpl(`${baseUrl}${path}`, {
      method,
      signal: AbortSignal.timeout(timeoutMs),
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Request-ID": requestId,
        Accept: "application/json",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store", // personal data: never cache across users
    });
  } catch {
    // Timeout, connection refused, DNS failure: the service didn't answer.
    return { ok: false, reason: "unavailable", status: null };
  }

  if (response.status === 204) return { ok: true, data: undefined as T };
  if (response.ok) {
    try {
      return { ok: true, data: (await response.json()) as T };
    } catch {
      return { ok: false, reason: "error", status: response.status };
    }
  }

  const status = response.status;
  if (status === 401) return { ok: false, reason: "unauthorized", status };
  if (status === 404) return { ok: false, reason: "not_found", status };
  if (status === 422) return { ok: false, reason: "invalid", status, errors: await readErrors(response) };
  if (status === 503) return { ok: false, reason: "unavailable", status };
  return { ok: false, reason: "error", status };
}

async function readErrors(response: Response): Promise<FieldError[]> {
  try {
    const problem: unknown = await response.json();
    if (problem && typeof problem === "object" && Array.isArray((problem as { errors?: unknown }).errors)) {
      return (problem as { errors: FieldError[] }).errors;
    }
  } catch {
    // Not JSON: no details to report.
  }
  return [];
}

export function getMyPreferences(
  baseUrl: string,
  token: string,
  options: Omit<CallOptions, "method" | "body"> = {},
): Promise<UserServiceResult<Preferences>> {
  // A read changes nothing, so one retry is safe (bounded: never more than 2 attempts).
  return callUserService<Preferences>(baseUrl, "/v1/me/preferences", token, { retries: 1, ...options });
}
