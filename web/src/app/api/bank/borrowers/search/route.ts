// BFF: GET /api/bank/borrowers/search?inn=... → backend.

import { NextRequest } from "next/server";

import { proxyToBackend } from "@/lib/bff";

export async function GET(req: NextRequest) {
  const inn = req.nextUrl.searchParams.get("inn") ?? "";
  return proxyToBackend(
    `/api/bank/borrowers/search?inn=${encodeURIComponent(inn)}`,
  );
}
