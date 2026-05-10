// BFF: GET /api/dossier/[id]/pdf — стрим backend-ответа в браузер.
// На bank install обязателен Bearer (backend требует auth); на accountant —
// header просто не добавляется, endpoint открыт. Same-origin URL позволяет
// открывать ссылку в новой вкладке без CORS/credentials проблем.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL } from "@/lib/config";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;

  const headers: Record<string, string> = {};
  if (access) headers.Authorization = `Bearer ${access}`;

  const upstream = await fetch(`${API_URL}/api/dossier/${id}/pdf`, {
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
