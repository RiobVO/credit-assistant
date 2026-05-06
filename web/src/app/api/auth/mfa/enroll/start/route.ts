// BFF: POST /api/auth/mfa/enroll/start → backend /api/bank/auth/mfa/enroll/start.
// Требует auth (Authorization: Bearer из ca_access cookie).
// Backend возвращает {secret, provisioning_uri}. Передаём как есть — secret нужен
// frontend'у для рендера QR и manual-entry fallback. Этот секрет существует
// только в session-state модалки и удаляется на unmount.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";

export async function POST() {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  if (!access) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const upstream = await fetch(`${API_URL}/api/bank/auth/mfa/enroll/start`, {
    method: "POST",
    headers: { Authorization: `Bearer ${access}` },
    cache: "no-store",
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
