// BFF: GET /api/dossier/[id]/pdf — стрим backend-ответа в браузер.
// На bank install обязателен Bearer (backend требует auth); на accountant —
// header просто не добавляется, endpoint открыт. Same-origin URL позволяет
// открывать ссылку в новой вкладке без CORS/credentials проблем.
//
// T0.4 / ADR-0015: query-param ?lang= пробрасывается со стороны клиента
// (`/dossier/[id]` page кладёт current locale из cookie в URL); если client
// его не задал — BFF дополнительно читает cookie `ca_locale` и форвардит
// дальше. Backend fallback chain: explicit query → brand.default_lang → "ru".

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";
import { LOCALE_COOKIE, readLocaleCookie } from "@/lib/locale-cookie";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;

  const headers: Record<string, string> = {};
  if (access) headers.Authorization = `Bearer ${access}`;

  // Resolve lang: client query > ca_locale cookie > backend brand default.
  const reqUrl = new URL(req.url);
  const clientLang = reqUrl.searchParams.get("lang");
  const cookieLang = readLocaleCookie(store.get(LOCALE_COOKIE)?.value);
  const lang = clientLang ?? cookieLang;

  const upstreamUrl = new URL(`${API_URL}/api/dossier/${id}/pdf`);
  if (lang) upstreamUrl.searchParams.set("lang", lang);

  const upstream = await fetch(upstreamUrl.toString(), {
    headers,
    cache: "no-store",
  });
  const body = await upstream.arrayBuffer();
  const respHeaders = new Headers();
  respHeaders.set(
    "Content-Type",
    upstream.headers.get("Content-Type") ?? "application/pdf",
  );
  const disp = upstream.headers.get("Content-Disposition");
  if (disp) respHeaders.set("Content-Disposition", disp);
  respHeaders.set("Cache-Control", "no-store");
  return new NextResponse(body, { status: upstream.status, headers: respHeaders });
}
