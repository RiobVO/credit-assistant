"use client";

import { Check, Copy, Info, Lock, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useAnalyst, type AnalystSummary } from "@/lib/auth";

const TIMEZONE_LABEL = "Asia/Tashkent · UTC+5";

function initialsFromName(full: string): string {
  const parts = full.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
}

function daysBetween(fromIso: string, now: Date): number {
  const from = new Date(fromIso);
  const ms = now.getTime() - from.getTime();
  return Math.max(0, Math.floor(ms / (24 * 60 * 60 * 1000)));
}

function formatRuLongDate(iso: string): string {
  // «11 мая 2026» — короткий неформальный вариант для read-only поля.
  // Без libs: ru-RU Intl даёт corretto.
  return new Date(iso).toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function roleLabel(t: ReturnType<typeof useTranslations>, role: string): string {
  if (role === "senior_analyst") return t("role_senior");
  if (role === "analyst") return t("role_analyst");
  return role;
}

export function ProfileSection() {
  const t = useTranslations("bank.settings");
  const { data: analyst, isLoading, isError } = useAnalyst();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-7 text-[13px] text-[var(--ink-3)]">
        {t("profile_loading")}
      </div>
    );
  }
  if (isError || !analyst) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-7 text-[13px] text-[var(--state-bad-fg)]">
        {t("profile_load_error")}
      </div>
    );
  }

  return <ProfileCard analyst={analyst} />;
}

function ProfileCard({ analyst }: { analyst: AnalystSummary }) {
  const t = useTranslations("bank.settings");
  const now = new Date();
  const passwordAgeDays = daysBetween(analyst.password_changed_at, now);
  const passwordFresh = passwordAgeDays <= 90;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <HeaderRow analyst={analyst} />
      <SecurityStrip
        mfa={analyst.mfa_enabled}
        passwordFresh={passwordFresh}
        passwordAgeDays={passwordAgeDays}
      />
      <div className="px-6 pt-4 pb-2">
        <h3 className="m-0 text-[14px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {t("section_account")}
        </h3>
      </div>
      <FieldsList analyst={analyst} />
      <FooterStrip />
    </div>
  );
}

function HeaderRow({ analyst }: { analyst: AnalystSummary }) {
  const t = useTranslations("bank.settings");
  // «09:14» — текущее время в Asia/Tashkent. Берём в client'е, т.к. SSR не знает
  // что показать (зависит от user-clock).
  const sessionLabel = useNowTashkent();
  return (
    <div className="flex items-center gap-3.5 border-b border-[var(--border)] px-6 py-4">
      <div className="grid size-11 place-items-center rounded-full bg-[var(--brand-primary)] text-[14px] font-semibold tracking-[0.02em] text-white">
        {initialsFromName(analyst.full_name)}
      </div>
      <div className="flex flex-1 flex-col gap-0.5 min-w-0">
        <div className="text-[14.5px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {analyst.full_name}
        </div>
        <div className="text-[12.5px] text-[var(--ink-3)]">{analyst.email}</div>
      </div>
      <span className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[var(--state-ok-fg)]">
        <span className="ds-pulse-ok size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
        {t("session_active")} · {sessionLabel}
      </span>
    </div>
  );
}

// Текущее время в Asia/Tashkent. Не реактивно: один раз на mount достаточно
// для «сеанс начался в 09:14», обновлять не нужно.
function useNowTashkent(): string {
  return new Date().toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tashkent",
  });
}

function SecurityStrip({
  mfa,
  passwordFresh,
  passwordAgeDays,
}: {
  mfa: boolean;
  passwordFresh: boolean;
  passwordAgeDays: number;
}) {
  const t = useTranslations("bank.settings");
  const sub = t("security_strip_sub", {
    mfa: mfa ? t("security_strip_mfa_yes") : "",
    password: passwordFresh
      ? t("security_strip_password_fresh", { days: passwordAgeDays })
      : t("security_strip_password_stale", { days: passwordAgeDays }),
  });

  return (
    <div
      className="mx-6 my-4 grid items-center gap-4 rounded-xl border border-[var(--state-ok-border)] px-4 py-3.5"
      style={{
        background:
          "linear-gradient(135deg, var(--state-ok-bg) 0%, var(--surface) 70%)",
        gridTemplateColumns: "auto 1fr auto",
      }}
    >
      <div className="grid size-9 place-items-center rounded-lg bg-[color-mix(in_srgb,var(--state-ok-fg)_14%,transparent)] text-[var(--state-ok-fg)]">
        <ShieldCheck className="size-5" />
      </div>
      <div className="flex flex-col gap-0.5 min-w-0">
        <div className="text-[13px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {t("security_strip_title")}
        </div>
        <div className="text-[12px] text-[var(--ink-3)]">{sub}</div>
      </div>
      <div className="flex gap-1.5 flex-shrink-0">
        {mfa ? (
          <SecurityChip label={t("security_chip_mfa")} />
        ) : null}
        {passwordFresh ? (
          <SecurityChip label={t("security_chip_password")} />
        ) : null}
        <SecurityChip label={t("security_chip_network")} />
      </div>
    </div>
  );
}

function SecurityChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--state-ok-border)] bg-[var(--state-ok-bg)]/70 px-2.5 py-1 text-[11px] font-medium text-[var(--state-ok-fg)]">
      <Check className="size-2.5" strokeWidth={2.6} />
      {label}
    </span>
  );
}

function FieldsList({ analyst }: { analyst: AnalystSummary }) {
  const t = useTranslations("bank.settings");
  const rows: Array<{
    key: string;
    label: string;
    value: string;
    mono?: boolean;
    badge?: "managed";
    copyable?: boolean;
  }> = [
    {
      key: "full_name",
      label: t("field_full_name"),
      value: analyst.full_name,
      badge: "managed",
    },
    {
      key: "email",
      label: t("field_email"),
      value: analyst.email,
      badge: "managed",
    },
    {
      key: "role",
      label: t("field_role"),
      value: roleLabel(t, analyst.role),
    },
    {
      key: "id",
      label: t("field_id"),
      value: analyst.id,
      mono: true,
      copyable: true,
    },
    {
      key: "since",
      label: t("field_member_since"),
      value: formatRuLongDate(analyst.created_at),
    },
    {
      key: "tz",
      label: t("field_timezone"),
      value: TIMEZONE_LABEL,
    },
  ];

  return (
    <dl className="m-0 flex flex-col px-6">
      {rows.map((row, idx) => (
        <div
          key={row.key}
          className={`grid grid-cols-[180px_1fr_auto] items-center gap-4 py-3 ${
            idx < rows.length - 1 ? "border-b border-[var(--border)]" : ""
          }`}
        >
          <dt className="text-[12.5px] font-medium text-[var(--ink-2)]">{row.label}</dt>
          <dd
            className={`m-0 text-[13px] text-[var(--ink-1)] ${
              row.mono ? "font-mono text-[12px] text-[var(--ink-2)] break-all tabular-nums" : ""
            }`}
          >
            {row.value}
          </dd>
          <div className="flex justify-end">
            {row.badge === "managed" ? <ManagedBadge /> : null}
            {row.copyable ? <CopyButton text={row.value} /> : null}
          </div>
        </div>
      ))}
    </dl>
  );
}

function ManagedBadge() {
  const t = useTranslations("bank.settings");
  return (
    <span className="inline-flex items-center gap-1.5 rounded bg-[var(--surface-3)] px-2 py-0.5 text-[10.5px] font-medium text-[var(--ink-3)]">
      <Lock className="size-2.5" />
      {t("field_managed_by_bank")}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const t = useTranslations("bank.settings");
  const [copied, setCopied] = useState(false);
  const handle = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard заблокирован — игнорируем тихо.
    }
  };
  return (
    <button
      type="button"
      onClick={handle}
      className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-transparent px-2 py-1 text-[11px] font-medium text-[var(--ink-3)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
    >
      {copied ? <Check className="size-2.5" strokeWidth={2.6} /> : <Copy className="size-2.5" />}
      {copied ? t("copied") : t("copy")}
    </button>
  );
}

function FooterStrip() {
  const t = useTranslations("bank.settings");
  return (
    <div className="mt-2 flex items-center justify-between gap-3 border-t border-[var(--border)] bg-[var(--surface-2)] px-6 py-3.5 text-[12px] text-[var(--ink-3)]">
      <span>{t("profile_footer_hint")}</span>
      <span className="inline-flex items-center gap-1.5">
        <Info className="size-3" />
        {t("profile_footer_help")}
      </span>
    </div>
  );
}
