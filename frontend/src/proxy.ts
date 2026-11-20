/**
 * Next.js 16 "proxy" (called middleware in Next.js 15 and earlier): code that runs before
 * every matching request.
 *
 * clerkMiddleware() reads the Clerk session cookie and makes `auth()` work in our server
 * code. It does NOT block any page by itself: each protected page checks the user with
 * `auth.protect()`, close to the data (Clerk's recommended pattern). The real security
 * boundary is still each backend service verifying the token (step 2.3).
 */
import { clerkMiddleware } from "@clerk/nextjs/server";
import { type NextFetchEvent, type NextRequest, NextResponse } from "next/server";

import { SIGN_IN_PATH, SIGN_UP_PATH } from "@/lib/auth-routes";

/** Liveness must not depend on outside services or config (same rule as /health in Python). */
const LIVENESS_PATH = "/api/health";

const clerk = clerkMiddleware({ signInUrl: SIGN_IN_PATH, signUpUrl: SIGN_UP_PATH });

export default function proxy(request: NextRequest, event: NextFetchEvent) {
  if (request.nextUrl.pathname === LIVENESS_PATH) {
    return NextResponse.next();
  }
  return clerk(request, event);
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
    // Always run for Clerk-specific frontend API routes
    "/__clerk/(.*)",
  ],
};
