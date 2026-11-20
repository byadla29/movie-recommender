import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Account deleted · Movie Discovery" };

/** Shown after an account is deleted. Static: it needs nothing about the (former) user. */
export default function GoodbyePage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Your account has been deleted</h1>
      <p className="mt-4 text-zinc-700 dark:text-zinc-300">
        Your preferences, privacy choices and sign-in details have been removed. Thanks for trying
        Movie Discovery.
      </p>
      <p className="mt-8">
        <Link href="/" className="font-medium underline underline-offset-4">
          Back to the start page
        </Link>
      </p>
    </main>
  );
}
