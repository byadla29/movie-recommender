import type { ServiceState, ServiceStatus } from "@/lib/api/health";

const STATE_LABEL: Record<ServiceState, string> = {
  ready: "Ready",
  not_ready: "Not ready",
  unreachable: "Unreachable",
  error: "Error",
};

// Colour is never the only signal: every state also has a text label (WCAG 1.4.1).
const STATE_STYLE: Record<ServiceState, string> = {
  ready: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-200",
  not_ready: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200",
  unreachable: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200",
  error: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200",
};

/** Presentational only: receives statuses as props, does no fetching. */
export function ServiceStatusList({ statuses }: { statuses: ServiceStatus[] }) {
  return (
    <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
      {statuses.map((status) => (
        <li key={status.name} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-medium">{status.name}</p>
            {Object.keys(status.checks).length > 0 && (
              <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-sm text-zinc-600 dark:text-zinc-400">
                {Object.entries(status.checks).map(([check, result]) => (
                  <div key={check} className="contents">
                    <dt>{check}</dt>
                    <dd>{result}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            {status.latencyMs !== null && (
              <span className="text-zinc-600 dark:text-zinc-400">{status.latencyMs} ms</span>
            )}
            <span className={`rounded-full px-2.5 py-0.5 font-medium ${STATE_STYLE[status.state]}`}>
              {STATE_LABEL[status.state]}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
