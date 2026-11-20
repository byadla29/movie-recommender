import "server-only";

import { auth, clerkClient } from "@clerk/nextjs/server";
import { unstable_rethrow } from "next/navigation";

/**
 * Delete the signed-in user's identity at Clerk (their email, password and sessions).
 *
 * This uses Clerk's Backend API with our SECRET key, which is why it can only run on the
 * server. Deleting the user also ends all of their sessions.
 * Returns false (and logs, without personal data) if Clerk couldn't be reached or refused.
 */
export async function deleteCurrentIdentity(): Promise<boolean> {
  const { userId } = await auth.protect();
  try {
    const client = await clerkClient();
    await client.users.deleteUser(userId);
    return true;
  } catch (error) {
    unstable_rethrow(error); // never swallow Next.js's own control-flow signals
    console.warn(
      JSON.stringify({
        level: "warn",
        message: "identity deletion failed",
        error: error instanceof Error ? error.name : "unknown",
      }),
    );
    return false;
  }
}
