"use client";

import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

import { ApiError } from "@/lib/api";
import { APP_MODE } from "@/lib/config";

// Экран ошибки: отдельная разводка для 404 и для остального (network/500).
// Back-link зависит от режима (история в bank, форма в accountant).

const BACK =
  APP_MODE === "bank"
    ? { href: "/history", label: "К истории" }
    : { href: "/manual-input", label: "К форме" };

export function DossierError({
  error,
  onRetry,
}: {
  dossierId: string;
  error: unknown;
  onRetry: () => void;
}) {
  const isNotFound = error instanceof ApiError && error.status === 404;

  return (
    <div className="mx-auto w-full max-w-[760px] px-8 pt-16 pb-12">
        <div className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] p-10 text-center shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-[#FCE7E5] text-[var(--state-bad-fg)]">
            <AlertCircle className="size-6" />
          </div>

          <h1 className="mt-4 text-[20px] font-semibold tracking-[-0.2px] text-[var(--ink-1)]">
            {isNotFound ? "Досье не найдено" : "Не удалось загрузить досье"}
          </h1>
          <p className="mx-auto mt-2 max-w-[480px] text-[14px] text-[var(--ink-3)]">
            {isNotFound
              ? "Возможно, ссылка устарела или досье было удалено. Создайте новое из формы ручного ввода."
              : "Попробуйте ещё раз. Если ошибка повторяется — проверьте, что бэкенд запущен и доступна база данных."}
          </p>

          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <Link
              href={BACK.href}
              className="inline-flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-[13px] font-medium text-[var(--ink-2)] transition-colors hover:bg-[#FAFBFC]"
            >
              <ArrowLeft className="size-4" />
              {BACK.label}
            </Link>
            {!isNotFound && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-2 rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[var(--brand-primary-hover)]"
              >
                <RefreshCw className="size-4" />
                Повторить
              </button>
            )}
          </div>
        </div>
    </div>
  );
}
