import { describe, expect, it, vi } from "vitest";

import { callUserService, getMyPreferences, type Preferences } from "./user-service";

const BASE = "http://user-service.test";
const TOKEN = "header.payload.signature-of-a-fake-token";

const PREFS: Preferences = {
  country_code: "IN",
  region_code: "IN-AP",
  languages: [
    { code: "te", rank: 1 },
    { code: "en", rank: 2 },
  ],
  genres: ["drama"],
  onboarded_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T10:00:00Z",
};

function respondWith(status: number, body?: unknown) {
  return vi.fn(async () =>
    body === undefined
      ? new Response(null, { status })
      : new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
}

describe("callUserService", () => {
  it("sends the user's token, a request id, and a timeout", async () => {
    const fetchImpl = respondWith(200, PREFS);

    await getMyPreferences(BASE, TOKEN, { fetchImpl, requestId: "req-123" });

    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${BASE}/v1/me/preferences`);
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
    expect(headers["X-Request-ID"]).toBe("req-123");
    expect(init.signal).toBeInstanceOf(AbortSignal);
    expect(init.cache).toBe("no-store");
  });

  it("sends JSON bodies for writes", async () => {
    const fetchImpl = respondWith(200, PREFS);

    await callUserService(BASE, "/v1/me/preferences", TOKEN, { method: "PUT", body: { a: 1 }, fetchImpl });

    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.method).toBe("PUT");
    expect(init.body).toBe('{"a":1}');
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("returns the data on 200", async () => {
    const result = await getMyPreferences(BASE, TOKEN, { fetchImpl: respondWith(200, PREFS) });

    expect(result).toEqual({ ok: true, data: PREFS });
  });

  it("treats 204 as success with no data", async () => {
    const result = await callUserService(BASE, "/v1/me", TOKEN, {
      method: "DELETE",
      fetchImpl: respondWith(204),
    });

    expect(result.ok).toBe(true);
  });

  it.each([
    [401, "unauthorized"],
    [404, "not_found"],
    [503, "unavailable"],
    [500, "error"],
    [418, "error"],
  ] as const)("maps HTTP %i to %s", async (status, reason) => {
    const result = await getMyPreferences(BASE, TOKEN, {
      fetchImpl: respondWith(status, { title: "x", status }),
    });

    expect(result).toEqual({ ok: false, reason, status });
  });

  it("passes on field errors from a 422", async () => {
    const errors = [{ loc: ["body", "languages", 0], msg: "Not a supported value", type: "unknown_code" }];

    const result = await callUserService(BASE, "/v1/me/preferences", TOKEN, {
      method: "PUT",
      body: {},
      fetchImpl: respondWith(422, { status: 422, errors }),
    });

    expect(result).toEqual({ ok: false, reason: "invalid", status: 422, errors });
  });

  it.each([
    ["a timeout", new DOMException("The operation timed out.", "TimeoutError")],
    ["connection refused", new TypeError("fetch failed")],
  ])("maps %s to unavailable", async (_case, error) => {
    const fetchImpl = vi.fn(async () => {
      throw error;
    });

    const result = await getMyPreferences(BASE, TOKEN, { fetchImpl });

    expect(result).toEqual({ ok: false, reason: "unavailable", status: null });
  });

  it("treats a 200 that isn't JSON as an error, not as data", async () => {
    const fetchImpl = vi.fn(async () => new Response("<html>oops</html>", { status: 200 }));

    const result = await getMyPreferences(BASE, TOKEN, { fetchImpl });

    expect(result).toEqual({ ok: false, reason: "error", status: 200 });
  });

  it("retries a read once when the service is unavailable, with the same request id", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(PREFS), { status: 200 }));

    const result = await getMyPreferences(BASE, TOKEN, { fetchImpl, requestId: "req-1" });

    expect(result).toEqual({ ok: true, data: PREFS });
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    const ids = fetchImpl.mock.calls.map(([, init]) => (init as RequestInit & { headers: Record<string, string> }).headers["X-Request-ID"]);
    expect(ids).toEqual(["req-1", "req-1"]);
  });

  it("gives up after one retry (bounded)", async () => {
    const fetchImpl = respondWith(503);

    const result = await getMyPreferences(BASE, TOKEN, { fetchImpl });

    expect(result).toEqual({ ok: false, reason: "unavailable", status: 503 });
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("does not retry answers that won't change (401, 404)", async () => {
    for (const status of [401, 404]) {
      const fetchImpl = respondWith(status);
      await getMyPreferences(BASE, TOKEN, { fetchImpl });
      expect(fetchImpl).toHaveBeenCalledOnce();
    }
  });

  it("does not retry writes unless asked to", async () => {
    const fetchImpl = respondWith(503);

    await callUserService(BASE, "/v1/me/preferences", TOKEN, { method: "PUT", body: {}, fetchImpl });

    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it("never puts the token into a result", async () => {
    for (const status of [200, 401, 404, 422, 500, 503]) {
      const result = await getMyPreferences(BASE, TOKEN, { fetchImpl: respondWith(status, PREFS) });
      expect(JSON.stringify(result)).not.toContain(TOKEN);
    }
  });
});
