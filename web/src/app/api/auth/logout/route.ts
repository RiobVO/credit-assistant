// BFF: POST /api/auth/logout — best-effort backend audit + denylist refresh + clear cookies.
//
// T1.2 (CA-019): прокидываем refresh_token из ca_refresh cookie в backend body,
// чтобы он попал в denylist до натурального expiration. Защита от stolen-cookie
// сценария: украденный refresh 7д валиден без denylist'а.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, API_URL, REFRESH_COOKIE } from "@/lib/config";

export async function POST() {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  const refresh = store.get(REFRESH_COOKIE)?.value;

  // Best-effort: даже если backend недоступен — cookies всё равно очищаем.
  if (access) {
    try {
      await fetch(`${API_URL}/api/bank/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${access}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(refresh ? { refresh_token: refresh } : {}),
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
