// BFF: POST /api/auth/logout — best-effort backend audit + clear cookies.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL, REFRESH_COOKIE } from "@/lib/config";

export async function POST() {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;

  // Best-effort: даже если backend недоступен — cookies всё равно очищаем.
  if (access) {
    try {
      await fetch(`${API_URL}/api/bank/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${access}` },
      });
    } catch {
      // ignore — главное удалить cookie
    }
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete({ name: ACCESS_COOKIE, path: "/" });
  response.cookies.delete({ name: REFRESH_COOKIE, path: "/api/auth" });
  return response;
}
