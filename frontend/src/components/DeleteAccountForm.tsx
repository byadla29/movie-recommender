"use client";

import { useClerk } from "@clerk/nextjs";
import { useActionState, useEffect } from "react";

import { DELETE_CONFIRMATION, type DeleteState } from "@/lib/settings";

type DeleteAction = (previous: DeleteState, formData: FormData) => Promise<DeleteState>;

export const GOODBYE_PATH = "/goodbye";

/**
 * Permanently delete the account. Two safeguards against accidents: the user must type
 * DELETE (checked again on the server), and the button says exactly what will happen.
 */
export function DeleteAccountForm({ action }: { action: DeleteAction }) {
  const [state, formAction, pending] = useActionState(action, { status: "idle", message: null });
  const { signOut } = useClerk();

  useEffect(() => {
    // Account gone: end the browser's session too and show the goodbye page.
    if (state.status === "deleted") void signOut({ redirectUrl: GOODBYE_PATH });
  }, [state.status, signOut]);

  if (state.status === "deleted") {
    return (
      <p role="status" className="mt-4 font-medium">
        Your account has been deleted. Signing you out…
      </p>
    );
  }

  return (
    <form action={formAction} className="mt-4 space-y-3">
      <label htmlFor="confirmation" className="block font-medium">
        Type <strong>{DELETE_CONFIRMATION}</strong> to confirm
      </label>
      <input
        id="confirmation"
        name="confirmation"
        type="text"
        required
        autoComplete="off"
        pattern={DELETE_CONFIRMATION}
        aria-describedby="delete-warning"
        aria-invalid={state.status === "error"}
        className="block w-full max-w-xs rounded-md border border-zinc-300 bg-white px-3 py-2 text-zinc-900 focus-visible:outline-2 focus-visible:outline-offset-2 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
      />
      <p id="delete-warning" className="text-sm text-zinc-600 dark:text-zinc-400">
        This permanently deletes your preferences, privacy choices and sign-in details. It can&apos;t be
        undone.
      </p>
      {state.message && (
        <p role="alert" className="font-medium text-red-700 dark:text-red-400">
          {state.message}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-red-700 px-4 py-2 font-medium text-white hover:bg-red-800 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60"
      >
        {pending ? "Deleting…" : "Delete my account permanently"}
      </button>
    </form>
  );
}
