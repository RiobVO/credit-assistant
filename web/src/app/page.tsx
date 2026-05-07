"use client";

import { useQuery } from "@tanstack/react-query";
import { API_URL } from "@/lib/config";

type Health = {
  status: string;
  version: string;
};

async function fetchHealth(): Promise<Health> {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json() as Promise<Health>;
}

export default function HomePage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">
        Credit Assistant — Phase 0
      </h1>
      <p className="text-muted-foreground max-w-md text-center text-sm">
        Главная задача: убедиться, что фронт видит бэкенд через <code>/health</code>.
      </p>

      <section
        className="w-full max-w-md rounded-lg border bg-card p-6 shadow-sm"
        aria-live="polite"
      >
        <h2 className="text-sm font-medium text-muted-foreground">
          Состояние API
        </h2>
        {isLoading && (
          <p className="mt-2 text-base">Проверяем соединение…</p>
        )}
        {isError && (
          <p className="mt-2 text-base text-red-600">
            Не удалось подключиться: {(error as Error).message}
          </p>
        )}
        {data && (
          <dl className="mt-2 grid grid-cols-[6rem_1fr] gap-y-1 text-base">
            <dt className="text-muted-foreground">status</dt>
            <dd className="font-mono">{data.status}</dd>
            <dt className="text-muted-foreground">version</dt>
            <dd className="font-mono">{data.version}</dd>
          </dl>
        )}
      </section>

      <p className="text-xs text-muted-foreground">
        API: <code>{API_URL}</code>
      </p>
    </main>
  );
}
