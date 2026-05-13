// BFF: POST /api/auth/mfa/challenge → backend /api/bank/auth/mfa/challenge.
// БЕЗ auth-cookie (это и есть login step-2 — у пользователя ещё нет access-token).
// Body: {challenge_token, code, use_backup_code}.
// При успехе backend возвращает LoginResponse — пакуем tokens в cookies,
// frontend получает только AnalystSummary (тот же pattern что /api/auth/login).

import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL, REFRESH_COOKIE } from "@/lib/config";

type BackendLoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  analyst: {
    id: string;
    email: string;
    full_name: string;
    role: string;
    created_at: string;
    password_changed_at: string;
    mfa_enabled: boolean;
  };
};

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "invalid_json" }, { status: 400 });
  }

  const upstream = await fetch(`${API_URL}/api/bank/auth/mfa/challenge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const upstreamBody = await upstream.text();
    return new NextResponse(upstreamBody, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  const data = (await upstream.json()) as BackendLoginResponse;
  const response = NextResponse.json(data.analyst);

  const isProd = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_COOKIE, data.access_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60,
  });
  response.cookies.set(REFRESH_COOKIE, data.refresh_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 7 * 24 * 60 * 60,
  });

  return response;
}
