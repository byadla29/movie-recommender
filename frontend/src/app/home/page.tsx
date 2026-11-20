import type { Metadata } from "next";
import { Suspense } from "react";

import { PreferencesSummary } from "@/components/PreferencesSummary";
import { getMyPreferencesAsCurrentUser } from "@/lib/api/user-service.server";

export const metadata: Metadata = { title: "Home · Movie Discovery" };

/**
 * Home for signed-in users. For now it shows what user-service knows about you; personalized
 * recommendation rows arrive in Phase 4.
 */
export default function HomePage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Your home</h1>
      <section aria-labelledby="prefs-heading" className="mt-8">
        <h2 id="prefs-heading" className="text-lg font-semibold">
          Your preferences
        </h2>
        <Suspense fallback={<p role="status" className="mt-4">Loading your preferences…</p>}>
          <MyPreferences />
        </Suspense>
      </section>
    </main>
  );
}

async function MyPreferences() {
  // Signed out → redirected to /sign-in inside this call (and back here afterwards).
  const result = await getMyPreferencesAsCurrentUser();
  return <PreferencesSummary result={result} />;
}
