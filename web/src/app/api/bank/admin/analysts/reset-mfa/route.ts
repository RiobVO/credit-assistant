// BFF: POST /api/bank/admin/analysts/reset-mfa → backend same path.
// Auth-required. Backend сам проверит role=senior_analyst и вернёт 403, если
// нет. Передаём body {email} as-is.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";

export async function POST(req: Request) {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  if (!access) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "invalid_json" }, { status: 400 });
  }

  const upstream = await fetch(`${API_URL}/api/bank/admin/analysts/reset-mfa`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${access}`,
    },
    body: JSON.stringify(body),
  });
  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
