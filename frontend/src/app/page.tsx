import Link from "next/link";

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
      <p className="mt-8 text-sm text-zinc-600 dark:text-zinc-400">
        Sign-up arrives in Phase 2. Developers:{" "}
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
