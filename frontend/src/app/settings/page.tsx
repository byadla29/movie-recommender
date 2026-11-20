import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { DeleteAccountForm } from "@/components/DeleteAccountForm";
import { PreferencesSummary } from "@/components/PreferencesSummary";
import { TrackingToggle } from "@/components/TrackingToggle";
import {
  getMyConsentsAsCurrentUser,
  getMyPreferencesAsCurrentUser,
} from "@/lib/api/user-service.server";
import { TRACKING_PURPOSE } from "@/lib/onboarding";

import { deleteAccount, setTracking } from "./actions";

export const metadata: Metadata = { title: "Settings · Movie Discovery" };

const section = "rounded-lg border border-zinc-200 p-6 dark:border-zinc-800";

/** Your preferences, your privacy choices, and deleting your account. Signed-in users only. */
export default function SettingsPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 space-y-8 px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>

      <section aria-labelledby="preferences-heading" className={section}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="preferences-heading" className="text-lg font-semibold">
            Your preferences
          </h2>
          <Link href="/onboarding" className="text-sm font-medium underline underline-offset-4">
            Edit
          </Link>
        </div>
        <Suspense fallback={<p role="status" className="mt-4">Loading…</p>}>
          <Preferences />
        </Suspense>
      </section>

      <section aria-labelledby="privacy-heading" className={section}>
        <h2 id="privacy-heading" className="text-lg font-semibold">
          Privacy
        </h2>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          We store your country, optional region, languages, genres and this choice. We don&apos;t store
          your name or email; sign-in is handled by our identity provider, Clerk.
        </p>
        <Suspense fallback={<p role="status" className="mt-4">Loading…</p>}>
          <Tracking />
        </Suspense>
      </section>

      <section aria-labelledby="delete-heading" className={`${section} border-red-300 dark:border-red-900`}>
        <h2 id="delete-heading" className="text-lg font-semibold">
          Delete account
        </h2>
        <DeleteAccountForm action={deleteAccount} />
      </section>
    </main>
  );
}

async function Preferences() {
  return <PreferencesSummary result={await getMyPreferencesAsCurrentUser()} />;
}

async function Tracking() {
  const result = await getMyConsentsAsCurrentUser();
  if (!result.ok) {
    return (
      <p role="alert" className="mt-4">
        We couldn&apos;t load your privacy choices. Please refresh the page in a moment.
      </p>
    );
  }
  const granted = result.data.consents.find((c) => c.purpose === TRACKING_PURPOSE)?.granted ?? false;
  return <TrackingToggle action={setTracking} initialGranted={granted} />;
}
