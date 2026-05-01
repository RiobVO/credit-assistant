"use client";

import { useEffect } from "react";

export default function BankError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error (bank):", error);
  }, [error]);

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg)] p-6">
      <div className="max-w-md rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h1 className="text-[18px] font-semibold text-[var(--ink-1)]">
          Что-то пошло не так
        </h1>
        <p className="mt-2 text-[13.5px] text-[var(--ink-3)]">
          Произошла непредвиденная ошибка. Попробуй обновить страницу. Если
          ошибка повторяется — сообщи в support с кодом{" "}
          <code className="font-mono text-[12px]">{error.digest ?? "—"}</code>.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-[var(--brand-primary-hover)]"
        >
          Попробовать снова
        </button>
      </div>
    </div>
  );
}
