import { SignIn } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Sign in · Movie Discovery" };

/**
 * Clerk's ready-made sign-in form. `[[...sign-in]]` is an optional catch-all route, so
 * Clerk's multi-step URLs (e.g. /sign-in/factor-one) all render this page.
 */
export default function SignInPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <Suspense fallback={<p role="status">Loading sign-in…</p>}>
        <SignIn />
      </Suspense>
    </main>
  );
}
