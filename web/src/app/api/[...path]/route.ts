// Catch-all BFF proxy: всё, что не покрыто явными `/api/auth/*`,
// `/api/bank/*`, `/api/dossier/[id]/pdf` route handler'ами, проксируется
// в backend с подстановкой `Authorization: Bearer <cookie>`. Решает Bug:
// shared endpoints (`/api/manual-input`, `/api/manual-input/draft`,
// `/api/upload/soliq-xltx`) на bank install требуют JWT, но cross-origin
// fetch из браузера cookie не отправляет. Same-origin через Next BFF —
// cookies автоматически идут на server-side, backend получает Bearer.

import { type NextRequest } from "next/server";

import { proxyRequest } from "@/lib/bff";

async function handler(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  const backendPath = `/api/${path.join("/")}${req.nextUrl.search}`;
  return proxyRequest(req, backendPath);
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
