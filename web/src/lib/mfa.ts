// Client-side helpers для 2FA enrollment / disable flow.
// Все запросы идут через BFF (`/api/auth/mfa/*`), JWT передаётся через
// httpOnly cookie — клиент Bearer не видит.

"use client";

import { AuthError } from "./auth";

export type EnrollStartResponse = {
  // base32 TOTP-секрет (~32 символа). Показывается пользователю как fallback
  // на случай если камера не работает. Должен быть введён вручную в authenticator.
  secret: string;
  // Полный otpauth:// URI с issuer + accountName + secret. Рендерится в QR.
  provisioning_uri: string;
};

export type EnrollVerifyResponse = {
  // 10 backup-кодов (8-значные). Показываются ровно один раз; backend хранит
  // их как bcrypt-хэши, plaintext больше нигде не увидим.
  backup_codes: string[];
};

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON body
    }
    throw new AuthError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export async function startEnroll(): Promise<EnrollStartResponse> {
  const resp = await fetch("/api/auth/mfa/enroll/start", {
    method: "POST",
    credentials: "same-origin",
  });
  return jsonOrThrow<EnrollStartResponse>(resp);
}

export async function verifyEnroll(code: string): Promise<EnrollVerifyResponse> {
  const resp = await fetch("/api/auth/mfa/enroll/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
    credentials: "same-origin",
  });
  return jsonOrThrow<EnrollVerifyResponse>(resp);
}

export async function disableMfa(args: {
  password: string;
  code: string;
}): Promise<void> {
  const resp = await fetch("/api/auth/mfa/disable", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
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
