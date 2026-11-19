import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { ServiceStatusList } from "@/components/ServiceStatusList";
import { checkServiceReadiness } from "@/lib/api/health";
import { getServiceUrls } from "@/lib/config";

export const metadata: Metadata = { title: "System status · Movie Discovery" };

/** Developer page: is each backend service reachable from the BFF and ready? */
export default function StatusPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">System status</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        Readiness of each backend service, checked from the Next.js server (the browser never
        calls services directly).
      </p>
      <div className="mt-8">
        <Suspense fallback={<p role="status">Checking services…</p>}>
          <ServiceStatuses />
        </Suspense>
      </div>
    </main>
  );
}

async function ServiceStatuses() {
  // Status must be fresh on every request, never prerendered at build time.
  await connection();
  const urls = getServiceUrls();
  const statuses = await Promise.all(
    Object.entries(urls).map(([name, url]) => checkServiceReadiness(name, url)),
  );
  return <ServiceStatusList statuses={statuses} />;
}
