import { NextRequest } from "next/server";
import type { NextFetchEvent } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Replace Clerk with a spy: these tests are about OUR routing rule, not Clerk itself.
const clerkHandler = vi.hoisted(() => vi.fn(() => new Response("handled by clerk")));
vi.mock("@clerk/nextjs/server", () => ({ clerkMiddleware: () => clerkHandler }));

const { default: proxy } = await import("./proxy");

const event = {} as NextFetchEvent;
const request = (path: string) => new NextRequest(new URL(path, "http://127.0.0.1:3000"));

describe("proxy", () => {
  beforeEach(() => clerkHandler.mockClear());

  it("lets the liveness check through without Clerk", async () => {
    const response = await proxy(request("/api/health"), event);

    expect(clerkHandler).not.toHaveBeenCalled();
    expect(response?.headers.get("x-middleware-next")).toBe("1"); // NextResponse.next()
  });

  it.each(["/", "/home", "/sign-in", "/api/other", "/api/health/extra"])(
    "sends %s through Clerk",
    async (path) => {
      await proxy(request(path), event);

      expect(clerkHandler).toHaveBeenCalledOnce();
    },
  );
});
