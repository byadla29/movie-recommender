"use server";

/**
 * Server Action for the onboarding form. Runs on our Next.js server when the form is
 * submitted, even if the browser has JavaScript turned off.
 *
 * Security: a Server Action is a public endpoint, so it never trusts that the page was
 * protected. Every user-service call below checks the session itself (auth.protect), and
 * user-service checks the token again.
 */
import { redirect } from "next/navigation";

import type { FailureReason } from "@/lib/api/user-service";
import {
  putMyConsentAsCurrentUser,
  putMyPreferencesAsCurrentUser,
} from "@/lib/api/user-service.server";
import {
  checkOnboarding,
  type FieldErrors,
  fieldErrorsFromServer,
  type OnboardingState,
  readOnboardingForm,
  toPreferencesInput,
  TRACKING_PURPOSE,
} from "@/lib/onboarding";

const PROBLEM_MESSAGES: Record<FailureReason, string> = {
  unauthorized: "Your session has expired. Please sign in again.",
  unavailable: "We couldn't save right now. Your choices are still here; please try again in a moment.",
  invalid: "Some of your choices couldn't be saved. Please review them and try again.",
  not_found: "Something went wrong while saving. Please try again.",
  error: "Something went wrong while saving. Please try again.",
};

export async function saveOnboarding(previous: OnboardingState, formData: FormData): Promise<OnboardingState> {
  const values = readOnboardingForm(formData);
  const reply = (errors: FieldErrors): OnboardingState => ({
    values, // send the user's choices back, so nothing they picked is lost
    errors,
    submission: previous.submission + 1,
  });

  // 1. Quick friendly checks (user-service checks everything again).
  const problems = checkOnboarding(values);
  if (Object.keys(problems).length > 0) return reply(problems);

  // 2. Preferences first: they are required for the app to work.
  const saved = await putMyPreferencesAsCurrentUser(toPreferencesInput(values));
  if (!saved.ok) {
    return reply(
      saved.reason === "invalid"
        ? fieldErrorsFromServer(saved.errors ?? [])
        : { form: PROBLEM_MESSAGES[saved.reason] },
    );
  }

  // 3. Then the consent answer. Two separate calls are not one transaction: if this one
  //    fails, the preferences are already saved. That's safe because both are idempotent
  //    PUTs: submitting the same form again simply sets the same values again.
  const consent = await putMyConsentAsCurrentUser(TRACKING_PURPOSE, values.tracking);
  if (!consent.ok) {
    return reply({
      tracking: "Your preferences were saved, but your personalization choice wasn't. Please submit again.",
    });
  }

  redirect("/home");
}
