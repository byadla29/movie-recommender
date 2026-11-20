"use server";

/**
 * Server Actions for the settings page. Each one checks the session itself (through the
 * helpers it calls): an action is a public endpoint, whatever page its form is on.
 */
import {
  deleteMyAccountDataAsCurrentUser,
  putMyConsentAsCurrentUser,
} from "@/lib/api/user-service.server";
import { deleteCurrentIdentity } from "@/lib/identity.server";
import { TRACKING_PURPOSE } from "@/lib/onboarding";
import { DELETE_CONFIRMATION, type DeleteState, type TrackingState } from "@/lib/settings";

/** Switch personalization tracking on or off. Withdrawing is exactly as easy as granting. */
export async function setTracking(previous: TrackingState, formData: FormData): Promise<TrackingState> {
  const wanted = formData.get("granted");
  // Only the exact strings our buttons send count; anything else is ignored, never guessed.
  if (wanted !== "true" && wanted !== "false") return { ...previous, error: "Please try again." };
  const granted = wanted === "true";

  const result = await putMyConsentAsCurrentUser(TRACKING_PURPOSE, granted);
  if (!result.ok) {
    return { granted: previous.granted, error: "We couldn't save your choice. Please try again in a moment." };
  }
  return { granted: result.data.granted, error: null };
}

/**
 * Delete my account everywhere (docs/architecture.md, "Account deletion"):
 *   1. our data in user-service   (recommendation-service joins in Phase 5)
 *   2. the identity at Clerk      (last: if step 1 fails, the user can still sign in and retry)
 * Every step is idempotent, so pressing the button again after a failure is always safe.
 */
export async function deleteAccount(_previous: DeleteState, formData: FormData): Promise<DeleteState> {
  // The server checks the confirmation too: the browser's check can be bypassed.
  if (formData.get("confirmation") !== DELETE_CONFIRMATION) {
    return { status: "error", message: `Type ${DELETE_CONFIRMATION} in capital letters to confirm.` };
  }

  const data = await deleteMyAccountDataAsCurrentUser();
  if (!data.ok) {
    return {
      status: "error",
      message: "We couldn't delete your data right now. Nothing was deleted; please try again in a moment.",
    };
  }

  if (!(await deleteCurrentIdentity())) {
    return {
      status: "error",
      message:
        "Your movie data was deleted, but we couldn't remove your sign-in details. Please press the button again.",
    };
  }

  // The browser then signs out (see DeleteAccountForm) and shows the goodbye page.
  return { status: "deleted", message: null };
}
