// BFF proxy: POST /api/auth/login → backend /api/bank/auth/login.
// Backend возвращает JSON с tokens; мы пакуем их в httpOnly cookies и отдаём
// клиенту только summary аналитика (id/email/full_name/role).

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
  };
};

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "invalid_json" }, { status: 400 });
  }

  const upstream = await fetch(`${API_URL}/api/bank/auth/login`, {
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

  // access cookie — на весь сайт, чтобы middleware /search/history его видел.
  // TTL чуть больше backend JWT access (15м) — клиентский redirect на 401
  // обрабатывает истечение надёжнее, чем точное совпадение TTL.
  const isProd = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_COOKIE, data.access_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60,
  });
  // refresh cookie — узкий path /api/auth, чтобы не утекать в каждый request.
  response.cookies.set(REFRESH_COOKIE, data.refresh_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 7 * 24 * 60 * 60,
  });

  return response;
}
