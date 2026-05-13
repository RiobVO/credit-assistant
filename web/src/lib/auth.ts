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

export async function login(req: LoginRequest): Promise<AnalystSummary> {
  const resp = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
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
