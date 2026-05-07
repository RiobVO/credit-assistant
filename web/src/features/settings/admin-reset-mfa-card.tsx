"use client";

// CA-DS13: senior_analyst может сбросить 2FA коллеге, если тот потерял
// телефон + backup-codes. Сейчас UI спрятан в /settings → Безопасность под
// role-gate; в будущей admin-panel переедет туда.

import { AlertTriangle, Check, Loader2, ShieldOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { adminResetMfa } from "@/lib/admin";
import { AuthError } from "@/lib/auth";

type FormState =
  | { kind: "idle" }
  | { kind: "confirming"; email: string }
  | { kind: "submitting" }
  | { kind: "ok"; email: string }
  | { kind: "error"; message: string };

export function AdminResetMfaCard() {
  const t = useTranslations("bank.settings");
  const [email, setEmail] = useState("");
  const [state, setState] = useState<FormState>({ kind: "idle" });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (trimmed.length < 3) {
      setState({ kind: "error", message: t("admin_reset_mfa_email_invalid") });
      return;
    }
    setState({ kind: "confirming", email: trimmed });
  };

  const handleConfirm = async () => {
    if (state.kind !== "confirming") return;
    const target = state.email;
    setState({ kind: "submitting" });
    try {
      await adminResetMfa(target);
      setState({ kind: "ok", email: target });
      setEmail("");
    } catch (err) {
      setState({ kind: "error", message: mapErrorToMessage(err, t) });
    }
  };

  return (
    <div className="rounded-xl border border-[var(--state-warn-border)] bg-[var(--surface)] p-7">
      <div className="mb-3 flex items-start gap-3">
        <div className="grid size-9 place-items-center rounded-lg bg-[color-mix(in_srgb,var(--state-warn-fg)_12%,transparent)] text-[var(--state-warn-fg)]">
          <ShieldOff className="size-4" />
        </div>
        <div className="flex flex-col gap-1">
          <h3 className="text-[14px] font-bold text-[var(--ink-1)]">
            {t("admin_reset_mfa_title")}
          </h3>
          <p className="text-[12.5px] text-[var(--ink-3)]">
            {t("admin_reset_mfa_hint")}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid max-w-md gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-[12px] font-semibold text-[var(--ink-2)]">
            {t("admin_reset_mfa_field_email")}
            <span className="ml-1 text-[var(--brand-primary)]">*</span>
          </span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="off"
            required
            placeholder={t("admin_reset_mfa_email_placeholder")}
            className="h-10 rounded-lg border border-[var(--border)] bg-white px-3 text-[14px] text-[var(--ink-1)] outline-none transition-colors focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]"
          />
        </label>

        {state.kind === "error" ? (
          <p role="alert" className="text-[12.5px] text-[var(--state-bad-fg)]">
            {state.message}
          </p>
        ) : null}
        {state.kind === "ok" ? (
          <p
            role="status"
            className="inline-flex items-center gap-2 text-[12.5px] text-[var(--state-ok-fg)]"
          >
            <Check className="size-3.5" />{" "}
            {t("admin_reset_mfa_success", { email: state.email })}
          </p>
        ) : null}

        <div>
          <button
            type="submit"
            disabled={state.kind === "submitting" || state.kind === "confirming"}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] px-3.5 text-[13px] font-semibold text-[var(--state-warn-fg)] transition-colors hover:bg-[color-mix(in_srgb,var(--state-warn-fg)_12%,var(--state-warn-bg))] disabled:cursor-not-allowed disabled:opacity-55"
          >
            <ShieldOff className="size-3.5" />
            {t("admin_reset_mfa_cta")}
          </button>
        </div>
      </form>

      {state.kind === "confirming" ? (
        <ConfirmModal
          email={state.email}
          onCancel={() => setState({ kind: "idle" })}
          onConfirm={() => void handleConfirm()}
        />
      ) : null}
      {state.kind === "submitting" ? (
        <ConfirmModal
          email={email}
          submitting
          onCancel={() => {
            /* disabled while submitting */
          }}
          onConfirm={() => {
            /* disabled while submitting */
          }}
        />
      ) : null}
    </div>
  );
}

function ConfirmModal({
  email,
  submitting,
  onCancel,
  onConfirm,
}: {
  email: string;
  submitting?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const t = useTranslations("bank.settings");
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-black/40 px-4"
    >
      <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-xl">
        <div className="mb-3 flex items-start gap-3">
          <div className="grid size-9 place-items-center rounded-lg bg-[color-mix(in_srgb,var(--state-warn-fg)_12%,transparent)] text-[var(--state-warn-fg)]">
            <AlertTriangle className="size-4" />
          </div>
          <div className="flex flex-col gap-1">
            <h4 className="text-[15px] font-bold text-[var(--ink-1)]">
              {t("admin_reset_mfa_confirm_title")}
            </h4>
            <p className="text-[13px] text-[var(--ink-2)]">
              {t("admin_reset_mfa_confirm_body", { email })}
            </p>
          </div>
        </div>
        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="inline-flex h-10 items-center rounded-md border border-[var(--border)] bg-white px-3.5 text-[13px] font-semibold text-[var(--ink-2)] transition-colors hover:bg-[var(--surface-2)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {t("admin_reset_mfa_cancel")}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={submitting}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-[var(--state-bad-fg)] px-3.5 text-[13px] font-semibold text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-55"
          >
            {submitting ? <Loader2 className="size-3.5 animate-spin" /> : null}
            {t("admin_reset_mfa_confirm_cta")}
          </button>
        </div>
      </div>
    </div>
  );
}

function mapErrorToMessage(
  err: unknown,
  t: ReturnType<typeof useTranslations>,
): string {
  if (err instanceof AuthError) {
    if (err.status === 403) return t("admin_reset_mfa_forbidden");
    if (err.status === 404) return t("admin_reset_mfa_not_found");
    if (err.status === 401) return t("admin_reset_mfa_unauthorized");
  }
  return err instanceof Error ? err.message : t("admin_reset_mfa_failed");
}
