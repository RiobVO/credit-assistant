"use client";

import { Check, Clock, KeyRound, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useAnalyst } from "@/lib/auth";
import { cn } from "@/lib/utils";

const PASSWORD_FRESH_THRESHOLD_DAYS = 90;

type PasswordStrength = {
  has12: boolean;
  hasDigit: boolean;
  hasUpper: boolean;
  hasSpecial: boolean;
};

function strengthFor(pw: string): PasswordStrength {
  return {
    has12: pw.length >= 12,
    hasDigit: /\d/.test(pw),
    hasUpper: /[A-ZА-ЯЁ]/.test(pw),
    hasSpecial: /[^\w\sа-яА-ЯёЁ]/.test(pw),
  };
}

function strengthScore(s: PasswordStrength): number {
  return (
    Number(s.has12) + Number(s.hasDigit) + Number(s.hasUpper) + Number(s.hasSpecial)
  );
}

function daysBetween(fromIso: string, now: Date): number {
  const from = new Date(fromIso);
  const ms = now.getTime() - from.getTime();
  return Math.max(0, Math.floor(ms / (24 * 60 * 60 * 1000)));
}

export function SecuritySection() {
  const t = useTranslations("bank.settings");
  const { data: analyst } = useAnalyst();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [state, setState] = useState<
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "ok" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });

  const strength = strengthFor(next);
  const score = strengthScore(strength);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < 12) {
      setState({ kind: "error", message: t("password_too_short") });
      return;
    }
    if (next !== confirm) {
      setState({ kind: "error", message: t("passwords_mismatch") });
      return;
    }
    setState({ kind: "submitting" });
    try {
      // TODO[CA-068]: backend endpoint `/api/auth/change-password` ещё не реализован.
      // Имитируем ответ для UX-flow; когда endpoint появится — подменим fetch.
      await new Promise((r) => setTimeout(r, 600));
      setState({ kind: "ok" });
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : t("password_change_failed"),
      });
    }
  };

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-7">
      {analyst ? (
        <PasswordStatusRow passwordChangedAt={analyst.password_changed_at} />
      ) : null}

      <form onSubmit={handleSubmit} className="grid max-w-md gap-4">
        <PasswordField
          label={t("field_current_password")}
          value={current}
          onChange={setCurrent}
          autoComplete="current-password"
          required
        />
        <div className="flex flex-col gap-1.5">
          <PasswordField
            label={t("field_new_password")}
            value={next}
            onChange={setNext}
            autoComplete="new-password"
            required
          />
          {next.length > 0 ? <StrengthMeter strength={strength} score={score} /> : null}
        </div>
        <PasswordField
          label={t("field_confirm_password")}
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
          required
        />

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
            <Check className="size-3.5" /> {t("password_updated")}
          </p>
        ) : null}

        <div className="flex items-center gap-2 pt-1">
          <button
            type="submit"
            disabled={state.kind === "submitting"}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-[var(--brand-primary)] px-3.5 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {state.kind === "submitting" ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <KeyRound className="size-3.5" />
            )}
            {t("change_password_cta")}
          </button>
          <span className="text-[11.5px] text-[var(--ink-4)]">{t("endpoint_wip")}</span>
        </div>
      </form>
    </div>
  );
}

function PasswordStatusRow({ passwordChangedAt }: { passwordChangedAt: string }) {
  const t = useTranslations("bank.settings");
  const days = daysBetween(passwordChangedAt, new Date());
  const fresh = days <= PASSWORD_FRESH_THRESHOLD_DAYS;
  const toneClasses = fresh
    ? "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)]"
    : "border-[var(--state-warn-border)] bg-[var(--state-warn-bg)]";
  const iconBg = fresh
    ? "bg-[color-mix(in_srgb,var(--state-ok-fg)_12%,transparent)] text-[var(--state-ok-fg)]"
    : "bg-[color-mix(in_srgb,var(--state-warn-fg)_12%,transparent)] text-[var(--state-warn-fg)]";
  const titleClass = fresh ? "text-[var(--state-ok-fg)]" : "text-[var(--state-warn-fg)]";

  return (
    <div
      className={cn(
        "mb-5 flex items-center gap-3 rounded-lg border px-4 py-3.5",
        toneClasses,
      )}
    >
      <div className={cn("grid size-9 place-items-center rounded-lg", iconBg)}>
        <Clock className="size-4" />
      </div>
      <div className="flex flex-col gap-0.5">
        <div className={cn("text-[13px] font-bold", titleClass)}>
          {fresh
            ? t("security_status_fresh", { days })
            : t("security_status_stale", { days })}
        </div>
        {!fresh ? (
          <div className="text-[12px] text-[var(--ink-3)]">
            {t("security_status_stale_hint")}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StrengthMeter({
  strength,
  score,
}: {
  strength: PasswordStrength;
  score: number;
}) {
  const t = useTranslations("bank.settings");
  const segments: Array<"bad" | "warn" | "ok" | "off"> = [
    score >= 1 ? (score < 2 ? "bad" : score < 3 ? "warn" : "ok") : "off",
    score >= 2 ? (score < 3 ? "warn" : "ok") : "off",
    score >= 3 ? "ok" : "off",
    score >= 4 ? "ok" : "off",
  ];
  const colorFor = (s: "bad" | "warn" | "ok" | "off"): string => {
    if (s === "ok") return "bg-[var(--state-ok-fg)]";
    if (s === "warn") return "bg-[var(--state-warn-fg)]";
    if (s === "bad") return "bg-[var(--state-bad-fg)]";
    return "bg-[var(--surface-3)]";
  };

  const items: Array<{ ok: boolean; label: string }> = [
    { ok: strength.has12, label: t("strength_12chars") },
    { ok: strength.hasDigit, label: t("strength_digit") },
    { ok: strength.hasUpper, label: t("strength_upper") },
    { ok: strength.hasSpecial, label: t("strength_special") },
  ];

  return (
    <div className="mt-1.5 flex flex-col gap-2">
      <div className="grid grid-cols-4 gap-[3px]">
        {segments.map((s, i) => (
          <span key={i} className={cn("h-1 rounded-[2px]", colorFor(s))} />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-y-1 gap-x-3.5 text-[11.5px]">
        {items.map((it) => (
          <span
            key={it.label}
            className={cn(
              "inline-flex items-center gap-1.5",
              it.ok ? "font-medium text-[var(--state-ok-fg)]" : "text-[var(--ink-3)]",
            )}
          >
            {it.ok ? (
              <Check className="size-2.5" strokeWidth={3} />
            ) : (
              <span className="size-2.5 rounded-full border border-[var(--ink-4)]" />
            )}
            {it.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[12px] font-semibold text-[var(--ink-2)]">
        {label}
        {required ? (
          <span className="ml-1 text-[var(--brand-primary)]">*</span>
        ) : null}
      </span>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required={required}
        className="h-10 rounded-lg border border-[var(--border)] bg-white px-3 text-[14px] text-[var(--ink-1)] outline-none transition-colors focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]"
      />
    </label>
  );
}
