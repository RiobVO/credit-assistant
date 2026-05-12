"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("shared.states");
  const tCta = useTranslations("shared.cta");

  useEffect(() => {
    // TODO[CA-064]: ship к real observability (Sentry/posthog) когда подключим.
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg)] p-6">
      <div className="max-w-md rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h1 className="text-[18px] font-semibold text-[var(--ink-1)]">
          {t("error_title")}
        </h1>
        <p className="mt-2 text-[13.5px] text-[var(--ink-3)]">
          {t("error_hint")}{" "}
          <code className="font-mono text-[12px]">{error.digest ?? "—"}</code>.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-[var(--brand-primary-hover)]"
        >
          {tCta("try_again")}
        </button>
      </div>
    </div>
  );
}
