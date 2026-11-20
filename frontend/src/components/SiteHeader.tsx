import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { Suspense } from "react";

/**
 * Top bar with the app name and the account controls.
 *
 * Whether someone is signed in is only known per request, so that part sits inside
 * <Suspense>: the rest of the header is static and shows instantly (Cache Components).
 */
export function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <nav
        aria-label="Main"
        className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-4 sm:px-6"
      >
        <Link
          href="/"
          className="font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          Movie Discovery
        </Link>
        <div className="flex min-w-32 items-center justify-end gap-3 text-sm">
          <Suspense fallback={null}>
            <Show when="signed-out">
              <SignInButton>
                <button type="button" className="rounded-md px-3 py-1.5 font-medium hover:bg-zinc-100 focus-visible:outline-2 dark:hover:bg-zinc-800">
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton>
                <button type="button" className="rounded-md bg-zinc-900 px-3 py-1.5 font-medium text-white hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300">
                  Sign up
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <Link href="/home" className="rounded-md px-3 py-1.5 font-medium hover:bg-zinc-100 focus-visible:outline-2 dark:hover:bg-zinc-800">
                Home
              </Link>
              <Link href="/settings" className="rounded-md px-3 py-1.5 font-medium hover:bg-zinc-100 focus-visible:outline-2 dark:hover:bg-zinc-800">
                Settings
              </Link>
              <UserButton />
            </Show>
          </Suspense>
        </div>
      </nav>
    </header>
  );
}
