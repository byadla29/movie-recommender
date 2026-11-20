import { auth } from "@clerk/nextjs/server";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Home · Movie Discovery" };

/**
 * Placeholder home page, only for signed-in users. Recommendations arrive in Phase 4;
 * step 2.7 connects this page to user-service.
 */
export default function HomePage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Your home</h1>
      <Suspense fallback={<p role="status" className="mt-4">Checking your session…</p>}>
        <SignedInContent />
      </Suspense>
    </main>
  );
}

async function SignedInContent() {
  // Signed out → redirected to /sign-in (and back here afterwards). Nothing below runs.
  const { userId } = await auth.protect();
  return (
    <div className="mt-4 space-y-2 text-zinc-700 dark:text-zinc-300">
      <p>You&apos;re signed in. Personalized rows will appear here in Phase 4.</p>
      <p className="text-sm text-zinc-500">
        Account ID: <code>{userId}</code>
      </p>
    </div>
  );
}
