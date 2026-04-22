// BFF: GET /api/bank/dossiers?filter=&q=&page=&page_size= → backend.

import { NextRequest } from "next/server";

import { proxyToBackend } from "@/lib/bff";

export async function GET(req: NextRequest) {
  const search = req.nextUrl.search; // "?filter=mine&q=..." или ""
  return proxyToBackend(`/api/bank/dossiers${search}`);
}
