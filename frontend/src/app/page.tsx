import Link from "next/link";

import { SIGN_UP_PATH } from "@/lib/auth-routes";

export default function LandingPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-4 py-16 sm:px-6">
      <p className="text-sm font-medium uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
        Movie discovery
      </p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
        Find films that fit your languages and taste.
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-zinc-700 dark:text-zinc-300">
        Tell us your region, the languages you watch in and the genres you enjoy. We&apos;ll
        recommend movies and explain why — and adapt as your interests change. This app is for
        discovery only; it does not stream films.
      </p>
      <div className="mt-8">
        <Link
          href={SIGN_UP_PATH}
          className="inline-block rounded-md bg-zinc-900 px-5 py-2.5 font-medium text-white hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Get started
        </Link>
      </div>
      <p className="mt-8 text-sm text-zinc-600 dark:text-zinc-400">
        Developers:{" "}
        <Link
          href="/status"
          className="font-medium underline underline-offset-4 hover:text-zinc-900 focus-visible:outline-2 focus-visible:outline-offset-2 dark:hover:text-zinc-100"
        >
          view system status
        </Link>
        .
      </p>
    </main>
  );
}
