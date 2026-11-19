/** Liveness for the frontend container: the Node server is up and serving routes. */
export function GET() {
  return Response.json({ status: "ok", service: "frontend" });
}
