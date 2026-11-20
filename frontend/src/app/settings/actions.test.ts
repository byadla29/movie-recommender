import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DeleteState, TrackingState } from "@/lib/settings";

// Replace the collaborators with fakes and record the ORDER in which they are called.
const calls: string[] = [];
const api = vi.hoisted(() => ({
  putMyConsentAsCurrentUser: vi.fn(),
  deleteMyAccountDataAsCurrentUser: vi.fn(),
}));
const identity = vi.hoisted(() => ({ deleteCurrentIdentity: vi.fn() }));
vi.mock("@/lib/api/user-service.server", () => api);
vi.mock("@/lib/identity.server", () => identity);

const { deleteAccount, setTracking } = await import("./actions");

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) data.append(key, value);
  return data;
}

const IDLE: DeleteState = { status: "idle", message: null };
const OFF: TrackingState = { granted: false, error: null };

describe("setTracking", () => {
  beforeEach(() => vi.clearAllMocks());

  it.each([
    ["true", true],
    ["false", false],
  ])("sends granted=%s to user-service", async (value, granted) => {
    api.putMyConsentAsCurrentUser.mockResolvedValue({ ok: true, data: { granted } });

    const state = await setTracking(OFF, form({ granted: value }));

    expect(api.putMyConsentAsCurrentUser).toHaveBeenCalledWith("personalization_tracking", granted);
    expect(state).toEqual({ granted, error: null });
  });

  it.each(["yes", "1", ""])("refuses to guess from %j", async (value) => {
    const state = await setTracking(OFF, form({ granted: value }));

    expect(api.putMyConsentAsCurrentUser).not.toHaveBeenCalled();
    expect(state.granted).toBe(false);
  });

  it("keeps the old value and explains when saving fails", async () => {
    api.putMyConsentAsCurrentUser.mockResolvedValue({ ok: false, reason: "unavailable", status: 503 });

    const state = await setTracking({ granted: true, error: null }, form({ granted: "false" }));

    expect(state.granted).toBe(true); // we don't pretend it changed
    expect(state.error).toMatch(/try again/);
  });
});

describe("deleteAccount", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    calls.length = 0;
    api.deleteMyAccountDataAsCurrentUser.mockImplementation(async () => {
      calls.push("user-service");
      return { ok: true, data: undefined };
    });
    identity.deleteCurrentIdentity.mockImplementation(async () => {
      calls.push("clerk");
      return true;
    });
  });

  it("deletes our data first, then the identity", async () => {
    const state = await deleteAccount(IDLE, form({ confirmation: "DELETE" }));

    expect(state).toEqual({ status: "deleted", message: null });
    expect(calls).toEqual(["user-service", "clerk"]);
  });

  it.each(["", "delete", "DELETE ", "yes"])("deletes nothing without the exact confirmation (%j)", async (typed) => {
    const state = await deleteAccount(IDLE, form({ confirmation: typed }));

    expect(state.status).toBe("error");
    expect(calls).toEqual([]);
  });

  it("keeps the identity when our data couldn't be deleted (user can sign in and retry)", async () => {
    api.deleteMyAccountDataAsCurrentUser.mockResolvedValue({ ok: false, reason: "unavailable", status: null });

    const state = await deleteAccount(IDLE, form({ confirmation: "DELETE" }));

    expect(state.status).toBe("error");
    expect(state.message).toMatch(/Nothing was deleted/);
    expect(identity.deleteCurrentIdentity).not.toHaveBeenCalled();
  });

  it("asks to press again if only the identity step failed (all steps are idempotent)", async () => {
    identity.deleteCurrentIdentity.mockResolvedValue(false);

    const state = await deleteAccount(IDLE, form({ confirmation: "DELETE" }));

    expect(state.status).toBe("error");
    expect(state.message).toMatch(/press the button again/);
  });
});
