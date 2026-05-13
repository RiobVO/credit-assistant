// BFF: GET /api/system/health → backend без auth (endpoint public).

import { NextResponse } from "next/server";

import { API_URL } from "@/lib/config";

export async function GET() {
  const upstream = await fetch(`${API_URL}/api/system/health`, {
    cache: "no-store",
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
