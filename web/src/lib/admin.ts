// Client-side helpers для admin-операций (CA-DS13). Доступны только senior_analyst,
// backend сам отвергнёт 403 если role не подходит — клиент не делает
// authorization-decision, только UI gating для UX.

"use client";

import { AuthError } from "./auth";

export async function adminResetMfa(email: string): Promise<void> {
  const resp = await fetch("/api/bank/admin/analysts/reset-mfa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
    credentials: "same-origin",
  });
  if (!resp.ok) {
    let detail = `${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON
    }
    throw new AuthError(resp.status, detail);
  }
}
