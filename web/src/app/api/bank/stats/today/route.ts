// BFF: GET /api/bank/stats/today → backend.

import { proxyToBackend } from "@/lib/bff";

export async function GET() {
  return proxyToBackend("/api/bank/stats/today");
}
