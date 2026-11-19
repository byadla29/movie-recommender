/**
 * Server-side readiness checks against backend services: the first example of the BFF
 * talking to services. Every call has a timeout, so one slow service can't hang the page
 * (docs/service-communication.md §1).
 */

export type ServiceState = "ready" | "not_ready" | "unreachable" | "error";

export interface ServiceStatus {
  name: string;
  state: ServiceState;
  /** Per-check results reported by the service's /ready endpoint, if any. */
  checks: Record<string, string>;
  latencyMs: number | null;
}

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export async function checkServiceReadiness(
  name: string,
  baseUrl: string,
  options: { fetchImpl?: FetchLike; timeoutMs?: number; requestId?: string } = {},
): Promise<ServiceStatus> {
  const { fetchImpl = fetch, timeoutMs = 1500, requestId = crypto.randomUUID() } = options;
  const started = performance.now();

  let response: Response;
  try {
    response = await fetchImpl(`${baseUrl}/ready`, {
      signal: AbortSignal.timeout(timeoutMs),
      headers: { "X-Request-ID": requestId, Accept: "application/json" },
      cache: "no-store",
    });
  } catch {
    // Network error, DNS failure or timeout: the service didn't answer at all.
    return { name, state: "unreachable", checks: {}, latencyMs: null };
  }

  const latencyMs = Math.round(performance.now() - started);
  const checks = await readChecks(response);

  if (response.status === 200) return { name, state: "ready", checks, latencyMs };
  if (response.status === 503) return { name, state: "not_ready", checks, latencyMs };
  return { name, state: "error", checks, latencyMs };
}

async function readChecks(response: Response): Promise<Record<string, string>> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "checks" in body) {
      const checks = (body as { checks: unknown }).checks;
      if (checks && typeof checks === "object") {
        return Object.fromEntries(
          Object.entries(checks).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
        );
      }
    }
  } catch {
    // Non-JSON body: nothing to report.
  }
  return {};
}
