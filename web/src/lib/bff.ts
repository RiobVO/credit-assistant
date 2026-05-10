// Server-only helpers: proxy запросов из браузера в backend с Bearer-токеном,
// поднятым из httpOnly cookie. Поддерживают как GET-обёртки (`proxyToBackend`),
// так и полный method/body pass-through (`proxyRequest`) для multipart/json POST.

import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";

// Заголовки, которые НЕ перебрасываем upstream: hop-by-hop + те, что
// fetch ставит сам (Content-Length по body, Host по target URL).
const STRIPPED_REQUEST_HEADERS = new Set([
  "host",
  "cookie",
  "content-length",
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "proxy-authorization",
  "proxy-authenticate",
  "authorization",
]);

// Те же hop-by-hop в обратную сторону.
const STRIPPED_RESPONSE_HEADERS = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "proxy-authorization",
  "proxy-authenticate",
]);

// Метод/body/headers напрямую пробрасываются в backend; cookie меняем на
// Authorization Bearer. Используется catch-all `app/api/[...path]/route.ts`.
export async function proxyRequest(
  req: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!STRIPPED_REQUEST_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    // arrayBuffer работает и для JSON, и для multipart/form-data — мы передаём
    // ровно те байты, что прислал клиент. Content-Type сохраняется в headers.
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(`${API_URL}${backendPath}`, init);

  const body = await upstream.arrayBuffer();
  const respHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIPPED_RESPONSE_HEADERS.has(key.toLowerCase())) {
      respHeaders.set(key, value);
    }
  });
  return new NextResponse(body, {
    status: upstream.status,
    headers: respHeaders,
  });
}

// Узкая обёртка для случаев, когда нам не нужен NextRequest (например,
// явный route handler хочет переписать backendPath). 401 если cookie нет.
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
