"use client";

// Модалка отключения 2FA. Требует текущий пароль (re-authentication) +
// действующий TOTP-код (или backup-код — но в этой v1 только TOTP).
// Backend проверит пароль через bcrypt, проверит код через текущий secret,
// затем NULL'нёт mfa_secret и удалит хэши backup-кодов.

import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, ShieldOff, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AuthError } from "@/lib/auth";
import { disableMfa } from "@/lib/mfa";

export function MfaDisableModal({ onClose }: { onClose: () => void }) {
  const t = useTranslations("bank.settings");
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Esc — закрывает только когда не идёт submit, чтобы не было race-condition
  // «закрыли модалку → запрос дошёл → mfa отключилась без UI feedback».
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [submitting, onClose]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    if (password.length === 0 || code.length !== 6) return;
    setSubmitting(true);
    setError(null);
    try {
      await disableMfa({ password, code });
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      onClose();
    } catch (err) {
      const msg =
        err instanceof AuthError && (err.status === 401 || err.status === 400)
          ? t("mfa_disable_invalid")
          : err instanceof Error
            ? err.message
            : t("mfa_disable_generic_error");
      setError(msg);
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="mfa-disable-title"
      className="fixed inset-0 z-[120] grid place-items-center bg-[color-mix(in_srgb,var(--ink-1)_55%,transparent)] backdrop-blur-[2px] p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_24px_48px_-12px_rgba(15,23,42,0.18)]">
        <header className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-6 py-4">
          <h2
            id="mfa-disable-title"
            className="m-0 text-[15.5px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]"
          >
            {t("mfa_disable_title")}
          </h2>
          <button
            type="button"
            aria-label={t("mfa_disable_cancel")}
            onClick={onClose}
            disabled={submitting}
            className="grid size-7 place-items-center rounded-md text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)] disabled:opacity-50"
          >
            <X className="size-4" />
          </button>
        </header>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-5">
          <div className="flex gap-3 rounded-lg border border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] p-3">
            <div className="grid size-8 flex-shrink-0 place-items-center rounded-lg bg-[color-mix(in_srgb,var(--state-warn-fg)_14%,transparent)] text-[var(--state-warn-fg)]">
              <AlertTriangle className="size-4" />
            </div>
            <p className="m-0 text-[12.5px] leading-[1.5] text-[var(--ink-2)]">
              {t("mfa_disable_warning")}
            </p>
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-semibold text-[var(--ink-2)]">
              {t("mfa_disable_password_label")}
            </span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
              required
              className="h-10 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-[14px] text-[var(--ink-1)] outline-none focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)] disabled:opacity-60"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-semibold text-[var(--ink-2)]">
              {t("mfa_disable_code_label")}
            </span>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) =>
                setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              disabled={submitting}
              required
              className="h-10 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 font-mono text-[14px] tracking-[0.3em] text-[var(--ink-1)] outline-none focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)] disabled:opacity-60"
            />
          </label>

          {error ? (
            <p role="alert" className="m-0 text-[12.5px] text-[var(--state-bad-fg)]">
              {error}
            </p>
          ) : null}

          <div className="mt-1 flex justify-between gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="inline-flex h-10 items-center rounded-md border border-[var(--border)] bg-transparent px-3.5 text-[12.5px] font-medium text-[var(--ink-2)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)] disabled:opacity-50"
            >
              {t("mfa_disable_cancel")}
            </button>
            <button
              type="submit"
              disabled={
                submitting || password.length === 0 || code.length !== 6
              }
              className="inline-flex h-10 items-center gap-2 rounded-md bg-[var(--state-bad-fg)] px-4 text-[13px] font-semibold text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-55"
            >
              {submitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  {t("mfa_disable_submitting")}
                </>
              ) : (
                <>
                  <ShieldOff className="size-3.5" />
                  {t("mfa_disable_cta")}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
