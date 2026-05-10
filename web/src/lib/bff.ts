// Server-only helper: proxy запросов из браузера в backend с Bearer-токеном,
// поднятым из httpOnly cookie. Возвращает NextResponse с body 1:1 от backend.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";

export async function proxyToBackend(
  backendPath: string,
  init: RequestInit = {},
): Promise<NextResponse> {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  if (!access) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${access}`);

  const upstream = await fetch(`${API_URL}${backendPath}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
