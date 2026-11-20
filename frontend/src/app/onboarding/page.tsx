import type { Metadata } from "next";
import { Suspense } from "react";

import { OnboardingForm } from "@/components/OnboardingForm";
import {
  getMyConsentsAsCurrentUser,
  getMyPreferencesAsCurrentUser,
} from "@/lib/api/user-service.server";
import { valuesFromSaved } from "@/lib/onboarding";

import { saveOnboarding } from "./actions";

export const metadata: Metadata = { title: "Your preferences · Movie Discovery" };

/** First-time setup, and later the place to change your choices. Signed-in users only. */
export default function OnboardingPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Tell us what you like to watch</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Four quick questions. You can change any answer later.
      </p>
      <Suspense fallback={<p role="status" className="mt-8">Loading your choices…</p>}>
        <OnboardingLoader />
      </Suspense>
    </main>
  );
}

async function OnboardingLoader() {
  // Both calls check the session first (signed out → redirected to sign-in).
  const [preferences, consents] = await Promise.all([
    getMyPreferencesAsCurrentUser(),
    getMyConsentsAsCurrentUser(),
  ]);

  const preferencesLoaded = preferences.ok || preferences.reason === "not_found";
  if (!preferencesLoaded || !consents.ok) {
    // Don't show an empty form that could overwrite saved choices we failed to load.
    return (
      <p role="alert" className="mt-8">
        We couldn&apos;t load your current choices. Please refresh the page in a moment.
      </p>
    );
  }

  return (
    <OnboardingForm
      action={saveOnboarding}
      initialValues={valuesFromSaved(preferences.ok ? preferences.data : null, consents.data.consents)}
      isEditing={preferences.ok}
    />
  );
}
