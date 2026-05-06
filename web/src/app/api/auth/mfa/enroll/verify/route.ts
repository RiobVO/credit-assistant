// BFF: POST /api/auth/mfa/enroll/verify → backend /api/bank/auth/mfa/enroll/verify.
// Auth-required. Body: {code}. Возвращает {backup_codes: string[10]} ровно один раз.
// Backend хранит коды как bcrypt-хэши; plaintext frontend больше не увидит.

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

  const upstream = await fetch(`${API_URL}/api/bank/auth/mfa/enroll/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${access}`,
    },
    body: JSON.stringify(body),
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
