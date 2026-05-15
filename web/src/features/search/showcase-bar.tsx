"use client";

import { cn } from "@/lib/utils";

// Phase 2 (DS-PHASE-2) — showcase-bar для быстрого переключения между
// состояниями /search. Удобно при demo банку / визуальной проверке: один
// клик и реальный backend-запрос с предзаготовленным ИНН.
//
// «Найдено» → 301234567 (Зумрад-Текстиль, approve, 12 мес sparkline)
// «Не найдено» → 999999999 (нет в БД)
// «Пустой» → reset в EmptyHero, без поиска
//
// Bar всегда видна — для demo. Если банк попросит спрятать в production —
// gate по URL `?showcase=1` или ENV.

export type ShowcaseKind = "result" | "notfound" | "idle";

const SHOWCASE_INNS: Record<ShowcaseKind, string> = {
  result: "301234567",
  notfound: "999999999",
  idle: "",
};

const LABELS: Record<ShowcaseKind, string> = {
  result: "Найдено",
  notfound: "Не найдено",
  idle: "Пустой",
};

export function ShowcaseBar({
  active,
  onPick,
}: {
  active: ShowcaseKind | null;
  onPick: (kind: ShowcaseKind, inn: string) => void;
}) {
  const items: ShowcaseKind[] = ["result", "notfound", "idle"];
  return (
    <div className="pointer-events-none fixed bottom-[18px] left-1/2 z-30 -translate-x-1/2">
      <div className="pointer-events-auto flex gap-1 rounded-[10px] bg-[rgba(14,21,37,0.92)] p-[5px] shadow-[0_12px_32px_-12px_rgba(14,21,37,0.55)] backdrop-blur-md">
        {items.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => onPick(k, SHOWCASE_INNS[k])}
            className={cn(
              "rounded-[7px] px-[14px] py-[7px] font-sans text-[11.5px] font-medium transition-colors",
              active === k
                ? "bg-white text-[#0E1525]"
                : "bg-transparent text-white/70 hover:text-white",
            )}
          >
            {LABELS[k]}
          </button>
        ))}
      </div>
    </div>
  );
}
