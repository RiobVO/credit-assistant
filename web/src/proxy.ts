// Next 16 proxy (бывший middleware): cookie-guard для bank-only страниц.
// Реальная валидация JWT — на backend; здесь проверяем только наличие cookie.
// Если пусто → redirect на /login. Login и BFF-роуты исключены из matcher'а.

import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_COOKIE } from "@/lib/config";

const PROTECTED = ["/search", "/history"];

export function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname;
  const isProtected = PROTECTED.some(
    (p) => path === p || path.startsWith(`${p}/`),
  );
  if (!isProtected) {
    return NextResponse.next();
  }
  if (req.cookies.get(ACCESS_COOKIE)?.value) {
    return NextResponse.next();
  }
  const loginUrl = new URL("/login", req.url);
  loginUrl.searchParams.set("next", path);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/search/:path*", "/history/:path*"],
};
