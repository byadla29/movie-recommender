import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DeleteState, TrackingState } from "@/lib/settings";

const signOut = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock("@clerk/nextjs", () => ({ useClerk: () => ({ signOut }) }));

const { DeleteAccountForm } = await import("./DeleteAccountForm");
const { TrackingToggle } = await import("./TrackingToggle");

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("TrackingToggle", () => {
  it("shows the current state and offers the opposite action", () => {
    render(<TrackingToggle action={async (s: TrackingState) => s} initialGranted={false} />);

    expect(screen.getByRole("status").textContent).toMatch(/is off/);
    expect(screen.getByRole("button", { name: "Turn on" })).toBeDefined();
  });

  it("flips after a successful save", async () => {
    const action = vi.fn(async (): Promise<TrackingState> => ({ granted: true, error: null }));
    render(<TrackingToggle action={action} initialGranted={false} />);

    fireEvent.click(screen.getByRole("button", { name: "Turn on" }));

    expect(await screen.findByRole("button", { name: "Turn off" })).toBeDefined();
    expect(screen.getByRole("status").textContent).toMatch(/is on/);
  });
});

describe("DeleteAccountForm", () => {
  it("requires typing DELETE and warns that it can't be undone", () => {
    render(<DeleteAccountForm action={async (s: DeleteState) => s} />);

    const input = screen.getByLabelText(/to confirm/) as HTMLInputElement;
    expect(input.required).toBe(true);
    expect(input.pattern).toBe("DELETE");
    expect(screen.getByText(/can.t be undone/)).toBeDefined();
  });

  it("signs out and goes to the goodbye page once the account is deleted", async () => {
    const action = vi.fn(async (): Promise<DeleteState> => ({ status: "deleted", message: null }));
    render(<DeleteAccountForm action={action} />);

    fireEvent.change(screen.getByLabelText(/to confirm/), { target: { value: "DELETE" } });
    fireEvent.click(screen.getByRole("button", { name: /Delete my account/ }));

    await waitFor(() => expect(signOut).toHaveBeenCalledWith({ redirectUrl: "/goodbye" }));
    expect(screen.getByRole("status").textContent).toMatch(/has been deleted/);
  });

  it("shows the server's message and does not sign out when deletion failed", async () => {
    const action = vi.fn(
      async (): Promise<DeleteState> => ({ status: "error", message: "Nothing was deleted; please try again." }),
    );
    render(<DeleteAccountForm action={action} />);

    fireEvent.change(screen.getByLabelText(/to confirm/), { target: { value: "DELETE" } });
    fireEvent.click(screen.getByRole("button", { name: /Delete my account/ }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/Nothing was deleted/);
    expect(signOut).not.toHaveBeenCalled();
  });
});
