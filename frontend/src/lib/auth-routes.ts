/**
 * Where sign-in lives and where people land afterwards. One place, used by the proxy,
 * the ClerkProvider and our pages, so the routes can't drift apart.
 */
export const SIGN_IN_PATH = "/sign-in";
export const SIGN_UP_PATH = "/sign-up";
/** Where a user goes after signing in/up when no other destination was requested. */
export const AFTER_AUTH_PATH = "/home";
