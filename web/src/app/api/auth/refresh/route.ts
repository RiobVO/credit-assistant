// BFF: POST /api/auth/refresh — обмен refresh-cookie на новую пару access+refresh.
// Клиент вызывает при 401 от /api/auth/me, до redirect на /login.
//
// T1.2 (CA-019): backend rotation. Каждый /refresh выдаёт новый refresh,
// старый сразу попадает в denylist. BFF обязан обновить ca_refresh cookie
// из upstream-ответа, иначе следующий /refresh пошлёт уже-denied токен → 401.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL, REFRESH_COOKIE } from "@/lib/config";

export async function POST() {
  const store = await cookies();
  const refresh = store.get(REFRESH_COOKIE)?.value;
  if (!refresh) {
    return NextResponse.json({ detail: "no_refresh" }, { status: 401 });
  }

  const upstream = await fetch(`${API_URL}/api/bank/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!upstream.ok) {
    // refresh невалиден (denylist / expired / inactive) — чистим cookies,
    // клиент пойдёт на /login.
    const response = NextResponse.json({ detail: "invalid_refresh" }, { status: 401 });
    response.cookies.delete({ name: ACCESS_COOKIE, path: "/" });
    response.cookies.delete({ name: REFRESH_COOKIE, path: "/api/auth" });
    return response;
  }

  const data = (await upstream.json()) as {
    access_token: string;
    refresh_token: string;
  };
  const response = new NextResponse(null, { status: 204 });
  const isProd = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_COOKIE, data.access_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60,
  });
  // T1.2: rotated refresh — обязательно обновить cookie. maxAge зеркалит
  // backend jwt_refresh_ttl_days (7д). Path /api/auth — узкий, чтобы refresh
  // не утекал в каждый request.
  response.cookies.set(REFRESH_COOKIE, data.refresh_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 7 * 24 * 60 * 60,
  });
  return response;
}
