import { SignUp } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Sign up · Movie Discovery" };

/** Clerk's ready-made sign-up form (passwords and emails are handled by Clerk, not us). */
export default function SignUpPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <Suspense fallback={<p role="status">Loading sign-up…</p>}>
        <SignUp />
      </Suspense>
    </main>
  );
}
