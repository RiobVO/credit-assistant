// BFF: GET /api/auth/me — проксирует backend `/api/bank/auth/me` с
// Authorization header из httpOnly cookie.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";

export async function GET() {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  if (!access) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const upstream = await fetch(`${API_URL}/api/bank/auth/me`, {
    headers: { Authorization: `Bearer ${access}` },
    cache: "no-store",
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
