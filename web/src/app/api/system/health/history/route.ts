// BFF: GET /api/system/health/history?days=N → backend без auth (endpoint public).

import { type NextRequest, NextResponse } from "next/server";

import { API_URL } from "@/lib/config";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const days = url.searchParams.get("days") ?? "30";
  const upstream = await fetch(
    `${API_URL}/api/system/health/history?days=${encodeURIComponent(days)}`,
    { cache: "no-store" },
  );
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
