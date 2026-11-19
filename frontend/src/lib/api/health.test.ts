import { describe, expect, it, vi } from "vitest";

import { checkServiceReadiness } from "./health";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("checkServiceReadiness", () => {
  it("reports ready with checks on 200", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(200, { status: "ready", checks: { database: "ok", migrations: "ok" } }),
    );

    const status = await checkServiceReadiness("user-service", "http://svc", { fetchImpl });

    expect(status.state).toBe("ready");
    expect(status.checks).toEqual({ database: "ok", migrations: "ok" });
    expect(status.latencyMs).toBeGreaterThanOrEqual(0);
  });

  it("calls /ready and forwards a request id", async () => {
    const fetchImpl = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () =>
      jsonResponse(200, {}),
    );

    await checkServiceReadiness("user-service", "http://svc:8000", { fetchImpl, requestId: "req-1" });

    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://svc:8000/ready");
    expect((init?.headers as Record<string, string>)["X-Request-ID"]).toBe("req-1");
    expect(init?.signal).toBeInstanceOf(AbortSignal);
  });

  it("reports not_ready with the failing checks on 503", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(503, { status: 503, checks: { database: "unreachable" } }),
    );

    const status = await checkServiceReadiness("catalog-service", "http://svc", { fetchImpl });

    expect(status).toMatchObject({ state: "not_ready", checks: { database: "unreachable" } });
  });

  it("reports unreachable when the request fails or times out", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new DOMException("timed out", "TimeoutError");
    });

    const status = await checkServiceReadiness("recommendation-service", "http://svc", { fetchImpl });

    expect(status).toEqual({ name: "recommendation-service", state: "unreachable", checks: {}, latencyMs: null });
  });

  it("reports error for unexpected statuses and tolerates non-JSON bodies", async () => {
    const fetchImpl = vi.fn(async () => new Response("<html>bad gateway</html>", { status: 502 }));

    const status = await checkServiceReadiness("user-service", "http://svc", { fetchImpl });

    expect(status).toMatchObject({ state: "error", checks: {} });
  });

  it("ignores non-string check values", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(200, { checks: { database: "ok", nested: { x: 1 } } }));

    const status = await checkServiceReadiness("user-service", "http://svc", { fetchImpl });

    expect(status.checks).toEqual({ database: "ok" });
  });
});
