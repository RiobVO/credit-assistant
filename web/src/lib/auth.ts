// Client-side auth helpers: тонкая обёртка над BFF /api/auth/*.
// Сами JWT никогда не попадают в JS — только AnalystSummary из /api/auth/me.

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export type AnalystSummary = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  // Phase 5 Settings: рендерятся в /settings → Профиль.
  // ISO 8601 timestamps; UI парсит через `new Date(...)`.
  created_at: string;
  password_changed_at: string;
  mfa_enabled: boolean;
};

export type LoginRequest = { email: string; password: string };

// Backend может ответить либо обычным LoginResponse (BFF превращает в AnalystSummary
// + ставит cookies), либо MFA-челленджем — пользователю придётся ввести TOTP.
// В случае челленджа cookies НЕ ставятся, а frontend переключается на step-2.
export type MfaChallenge = {
  requires_mfa: true;
  challenge_token: string;
};

export type LoginResult = AnalystSummary | MfaChallenge;

export function isMfaChallenge(r: LoginResult): r is MfaChallenge {
  return (r as MfaChallenge).requires_mfa === true;
}

export class AuthError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "AuthError";
  }
}

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore — non-JSON body
    }
    throw new AuthError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export async function login(req: LoginRequest): Promise<LoginResult> {
  const resp = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    credentials: "same-origin",
  });
  return jsonOrThrow<LoginResult>(resp);
}

// Step-2 login: пользователь вводит TOTP-код или backup-код, BFF идёт в
// `/api/bank/auth/mfa/challenge` с challenge_token, при успехе ставит cookies
// (тот же pattern что и login).
export async function submitMfaChallenge(args: {
  challenge_token: string;
  code: string;
  use_backup_code: boolean;
}): Promise<AnalystSummary> {
  const resp = await fetch("/api/auth/mfa/challenge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
    credentials: "same-origin",
  });
  return jsonOrThrow<AnalystSummary>(resp);
}

export async function fetchMe(): Promise<AnalystSummary> {
  const resp = await fetch("/api/auth/me", { credentials: "same-origin" });
  return jsonOrThrow<AnalystSummary>(resp);
}

export async function logout(): Promise<void> {
  const resp = await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "same-origin",
  });
  if (!resp.ok && resp.status !== 401) {
    // 401 = уже разлогинены, считаем успехом
    throw new AuthError(resp.status, `logout failed: ${resp.status}`);
  }
}

export function useAnalyst() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchMe,
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries({ queryKey: ["auth"] });
    },
  });
}
