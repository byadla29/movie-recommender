"use client";

import { useActionState } from "react";

import type { TrackingState } from "@/lib/settings";

type SetTracking = (previous: TrackingState, formData: FormData) => Promise<TrackingState>;

/**
 * Shows whether personalization tracking is on and offers ONE button to flip it.
 * Turning it off is exactly as easy as turning it on.
 */
export function TrackingToggle({ action, initialGranted }: { action: SetTracking; initialGranted: boolean }) {
  const [state, formAction, pending] = useActionState(action, { granted: initialGranted, error: null });

  return (
    <form action={formAction} className="mt-4 space-y-3">
      <p role="status">
        Personalization from your activity is <strong>{state.granted ? "on" : "off"}</strong>.
      </p>
      <input type="hidden" name="granted" value={state.granted ? "false" : "true"} />
      <button
        type="submit"
        disabled={pending}
        className="rounded-md border border-zinc-300 px-4 py-2 font-medium hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60 dark:border-zinc-700 dark:hover:bg-zinc-800"
      >
        {pending ? "Saving…" : state.granted ? "Turn off" : "Turn on"}
      </button>
      {state.error && (
        <p role="alert" className="font-medium text-red-700 dark:text-red-400">
          {state.error}
        </p>
      )}
    </form>
  );
}
