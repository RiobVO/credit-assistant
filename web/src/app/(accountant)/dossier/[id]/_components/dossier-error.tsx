"use client";

import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

import { Topbar } from "../../../_components/topbar";

import { ApiError } from "@/lib/api";

// Экран ошибки: отдельная разводка для 404 и для остального (network/500).
// Оба уводят пользователя обратно в список заявок (mock-link на /manual-input).

export function DossierError({
  dossierId,
  error,
  onRetry,
}: {
  dossierId: string;
  error: unknown;
  onRetry: () => void;
}) {
  const isNotFound = error instanceof ApiError && error.status === 404;

  return (
    <>
      <Topbar
        crumbs={[
          { label: "Заявки" },
          { label: "Досье" },
          { label: dossierId.slice(0, 8), current: true },
        ]}
      />
      <div className="w-full max-w-[760px] px-8 pt-16 pb-12">
        <div className="rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] p-10 text-center shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-[#FCE7E5] text-[var(--ca-danger)]">
            <AlertCircle className="size-6" />
          </div>

          <h1 className="mt-4 text-[20px] font-semibold tracking-[-0.2px] text-[var(--ca-ink-900)]">
            {isNotFound ? "Досье не найдено" : "Не удалось загрузить досье"}
          </h1>
          <p className="mx-auto mt-2 max-w-[480px] text-[14px] text-[var(--ca-ink-500)]">
            {isNotFound
              ? "Возможно, ссылка устарела или досье было удалено. Создайте новое из формы ручного ввода."
              : "Попробуйте ещё раз. Если ошибка повторяется — проверьте, что бэкенд запущен и доступна база данных."}
          </p>

          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <Link
              href="/manual-input"
              className="inline-flex items-center gap-2 rounded-md border border-[var(--ca-border)] bg-[var(--ca-surface)] px-4 py-2 text-[13px] font-medium text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]"
            >
              <ArrowLeft className="size-4" />К форме
            </Link>
            {!isNotFound && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-2 rounded-md bg-[var(--ca-primary-blue-700)] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[var(--ca-primary-blue-800)]"
              >
                <RefreshCw className="size-4" />
                Повторить
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
