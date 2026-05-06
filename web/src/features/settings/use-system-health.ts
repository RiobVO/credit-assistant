"use client";

// useQuery-обёртки над BFF /api/system/health и /api/system/health/history.
// Backend кеш-friendly: staleTime 60s для health (real-time-ish), 5min для history
// (меняется не чаще раза в день — UPSERT в БД).

import { useQuery } from "@tanstack/react-query";

export type ServiceStatus = {
  key: string;
  status: "ok" | "degraded" | "down" | "not_implemented";
  tip?: string | null;
};

export type SystemHealth = {
  status: "ok" | "degraded" | "down";
  checked_at: string;
  services: ServiceStatus[];
};

export type UptimeDay = {
  day: string;
  status: "ok" | "degraded" | "down";
};

export type UptimeHistory = {
  first_seen_day: string | null;
  days: UptimeDay[];
};

async function fetchSystemHealth(): Promise<SystemHealth> {
  const resp = await fetch("/api/system/health", { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`system_health: ${resp.status}`);
  return (await resp.json()) as SystemHealth;
}

async function fetchUptimeHistory(days = 30): Promise<UptimeHistory> {
  const resp = await fetch(`/api/system/health/history?days=${days}`, {
    credentials: "same-origin",
  });
  if (!resp.ok) throw new Error(`uptime_history: ${resp.status}`);
  return (await resp.json()) as UptimeHistory;
}

export function useSystemHealth() {
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: fetchSystemHealth,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useUptimeHistory(days = 30) {
  return useQuery({
    queryKey: ["system", "uptime", days],
    queryFn: () => fetchUptimeHistory(days),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
}
