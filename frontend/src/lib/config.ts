import "server-only";

/**
 * Backend service locations. Server-side only: the browser never talks to services
 * directly (docs/architecture.md §4), so these are deliberately NOT `NEXT_PUBLIC_*`.
 * Defaults match the ports Docker Compose publishes on localhost, for `npm run dev`.
 */
export type ServiceName = "user-service" | "catalog-service" | "recommendation-service";

export function getServiceUrls(env: NodeJS.ProcessEnv = process.env): Record<ServiceName, string> {
  return {
    "user-service": env.USER_SERVICE_URL ?? "http://127.0.0.1:8001",
    "catalog-service": env.CATALOG_SERVICE_URL ?? "http://127.0.0.1:8002",
    "recommendation-service": env.RECOMMENDATION_SERVICE_URL ?? "http://127.0.0.1:8003",
  };
}
