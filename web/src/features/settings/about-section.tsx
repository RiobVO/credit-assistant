"use client";

import {
  AlertTriangle,
  ChevronRight,
  Clock,
  Copy,
  Database,
  FileSearch,
  FileText,
  Search,
  Zap,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";

import { useBrand } from "@/lib/brand-context";
import { cn } from "@/lib/utils";

import {
  type ServiceStatus,
  useSystemHealth,
  useUptimeHistory,
} from "./use-system-health";

const APP_VERSION = process.env.NEXT_PUBLIC_BUILD_VERSION ?? "dev";
const APP_BUILD_SHA = process.env.NEXT_PUBLIC_BUILD_SHA ?? "—";
const APP_BUILD_DATE = process.env.NEXT_PUBLIC_BUILD_DATE ?? "—";
const API_VERSION = "v1.2";

export function AboutSection() {
  const t = useTranslations("bank.settings");
  const brand = useBrand();

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <Header brand={brand} />
      <HealthStrip />
      <div className="px-6 pt-4 pb-2">
        <h3 className="m-0 text-[14px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {t("about_title")}
        </h3>
      </div>
      <FieldsList />
      <FooterStrip />
    </div>
  );
}

function Header({
  brand,
}: {
  brand: { name: string; tagline: string; logoMark: string };
}) {
  return (
    <div className="flex items-center gap-3.5 border-b border-[var(--border)] px-6 py-4">
      <div className="grid size-10 place-items-center rounded-[9px] bg-[var(--brand-primary)] text-[13px] font-bold tracking-[0.04em] text-white">
        {brand.logoMark}
      </div>
      <div className="flex flex-1 flex-col gap-0.5 min-w-0">
        <div className="text-[14.5px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {brand.name}
        </div>
        <div className="text-[12.5px] text-[var(--ink-3)]">{brand.tagline}</div>
      </div>
      <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--state-ok-bg)] px-2.5 py-1 font-mono text-[11.5px] font-semibold text-[var(--state-ok-fg)]">
        <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
        v{APP_VERSION}
      </span>
    </div>
  );
}

function HealthStrip() {
  const t = useTranslations("bank.settings");
  const health = useSystemHealth();
  const history = useUptimeHistory(30);

  const overall: "ok" | "degraded" | "down" = health.data?.status ?? "ok";
  const checkedAt = health.data?.checked_at
    ? formatRelativeShort(new Date(health.data.checked_at))
    : t("profile_loading");
  const downCount =
    health.data?.services.filter((s) => s.status === "down").length ?? 0;

  let title = t("health_title");
  let sub = t("health_sub_ok", { when: checkedAt });
  if (overall === "degraded") {
    title = t("health_title_degraded");
    sub = t("health_sub_degraded", { when: checkedAt });
  } else if (overall === "down") {
    title = t("health_title_down");
    sub = t("health_sub_down", { when: checkedAt, count: downCount });
  }

  const okDays = (history.data?.days ?? []).filter((d) => d.status === "ok").length;

  return (
    <div
      className="mx-6 my-4 grid items-center gap-[18px] rounded-xl border border-[var(--state-ok-border)] px-[18px] py-4"
      style={{
        background:
          "linear-gradient(135deg, var(--state-ok-bg) 0%, var(--surface) 80%)",
        gridTemplateColumns: "auto 1fr auto",
      }}
    >
      <div className="relative grid size-11 place-items-center rounded-[11px] bg-[color-mix(in_srgb,var(--state-ok-fg)_16%,transparent)] text-[var(--state-ok-fg)]">
        <Zap className="size-5" />
        <span className="ds-pulse-ok pointer-events-none absolute inset-0 rounded-[11px]" />
      </div>
      <div className="flex flex-col gap-0.5 min-w-0">
        <div className="text-[14.5px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {title}
        </div>
        <div className="text-[12px] leading-[1.4] text-[var(--ink-3)]">{sub}</div>
      </div>
      <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
        <span className="text-[9.5px] font-bold uppercase tracking-[0.16em] text-[var(--ink-4)]">
          {t("uptime_label", { days: okDays })}
        </span>
        <UptimeCalendar history={history.data?.days ?? []} />
      </div>
    </div>
  );
}

function UptimeCalendar({
  history,
}: {
  history: Array<{ day: string; status: string }>;
}) {
  // Рендерим 30 квадратов. Дни без записи в БД — grey («до запуска»).
  // Today имеет ring-border.
  const today = new Date().toISOString().slice(0, 10);
  const byDay = new Map(history.map((d) => [d.day, d.status]));
  const days: Array<{ key: string; status: "ok" | "degraded" | "down" | "unknown"; isToday: boolean }> =
    [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const raw = byDay.get(key);
    const status =
      raw === "ok" || raw === "degraded" || raw === "down" ? raw : "unknown";
    days.push({ key, status, isToday: key === today });
  }

  return (
    <div className="flex gap-[3px]">
      {days.map((d) => (
        <span
          key={d.key}
          title={`${d.key} · ${d.status}`}
          className={cn(
            "h-[18px] w-[7px] rounded-[2px] transition-opacity hover:opacity-100",
            d.status === "ok" && "bg-[var(--state-ok-fg)] opacity-60",
            d.status === "degraded" && "bg-[var(--state-warn-fg)] opacity-85",
            d.status === "down" && "bg-[var(--state-bad-fg)] opacity-85",
            d.status === "unknown" && "bg-[var(--surface-3)] opacity-100",
            d.isToday && "shadow-[0_0_0_1.5px_var(--state-ok-fg)] opacity-100",
          )}
        />
      ))}
    </div>
  );
}

function formatRelativeShort(when: Date): string {
  const minutes = Math.floor((Date.now() - when.getTime()) / 60_000);
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  const days = Math.floor(hours / 24);
  return `${days} д назад`;
}

function FieldsList() {
  const t = useTranslations("bank.settings");
  return (
    <dl className="m-0 flex flex-col px-6">
      <SimpleRow label={t("field_version")} value={APP_VERSION} mono />
      <ExpandableRow
        label={t("release_notes_title")}
        value={t("release_notes_value", { date: APP_BUILD_DATE })}
        body={<ReleaseNotesPanel />}
      />
      <SimpleRow label={t("field_build")} value={APP_BUILD_SHA} mono copyable />
      <SimpleRow label={t("field_api")} value={API_VERSION} mono />
      <SimpleRow label={t("field_mode")} value="Bank Mode" />
      <SimpleRow label={t("field_environment")} value={t("env_on_premise")} />
      <ExpandableRow
        label={t("services_title")}
        value={<ServicesValueText />}
        body={<ServicesPanel />}
      />
      <SimpleRow label={t("field_locale")} value={t("locale_ru_full")} />
      <SimpleRow label={t("field_timezone")} value="Asia/Tashkent · UTC+5" last />
    </dl>
  );
}

function SimpleRow({
  label,
  value,
  mono,
  copyable,
  last,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
  copyable?: boolean;
  last?: boolean;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[180px_1fr_auto] items-center gap-4 py-3",
        !last && "border-b border-[var(--border)]",
      )}
    >
      <dt className="text-[12.5px] font-medium text-[var(--ink-2)]">{label}</dt>
      <dd
        className={cn(
          "m-0 text-[13px] text-[var(--ink-1)]",
          mono && "font-mono text-[12px] text-[var(--ink-2)] break-all tabular-nums",
        )}
      >
        {value}
      </dd>
      <div className="flex justify-end">
        {copyable && typeof value === "string" ? <CopyInline text={value} /> : null}
      </div>
    </div>
  );
}

function CopyInline({ text }: { text: string }) {
  const t = useTranslations("bank.settings");
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          // Clipboard заблокирован.
        }
      }}
      className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] px-2 py-1 text-[11px] font-medium text-[var(--ink-3)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
    >
      <Copy className="size-2.5" />
      {copied ? t("copied") : t("copy")}
    </button>
  );
}

function ExpandableRow({
  label,
  value,
  body,
}: {
  label: string;
  value: ReactNode;
  body: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-[var(--border)]">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="grid w-full cursor-pointer grid-cols-[180px_1fr_auto] items-center gap-4 border-0 bg-transparent py-3 pr-1 text-left transition-colors hover:bg-[var(--surface-2)]"
      >
        <span className="text-[12.5px] font-medium text-[var(--ink-2)]">{label}</span>
        <span className="text-[13px] text-[var(--ink-1)]">{value}</span>
        <ChevronRight
          className={cn(
            "size-4",
            open ? "text-[var(--brand-primary)]" : "text-[var(--ink-4)]",
          )}
          style={{
            transition: "transform 280ms cubic-bezier(0.34, 1.56, 0.64, 1), color 200ms ease",
            transform: open ? "rotate(90deg)" : "rotate(0deg)",
          }}
        />
      </button>
      {open ? (
        <div className="pb-3">
          <div
            className="rounded-r-lg border-l-2 border-[var(--brand-primary)] px-3 pt-2 pb-4"
            style={{
              background:
                "linear-gradient(90deg, var(--brand-primary-soft) 0%, transparent 60%)",
              animation: "ds-row-fade-in 220ms ease-out",
            }}
          >
            {body}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ReleaseNotesPanel() {
  const t = useTranslations("bank.settings");
  const items: Array<{ title: string; desc: string; icon: ReactNode }> = [
    {
      title: t("release_item_1_title"),
      desc: t("release_item_1_desc"),
      icon: <Search className="size-[18px]" />,
    },
    {
      title: t("release_item_2_title"),
      desc: t("release_item_2_desc"),
      icon: <FileText className="size-[18px]" />,
    },
    {
      title: t("release_item_3_title"),
      desc: t("release_item_3_desc"),
      icon: <Clock className="size-[18px]" />,
    },
  ];
  return (
    <div className="flex flex-col gap-3.5 pt-1">
      <div className="flex items-center gap-2.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--ink-4)]">
        <span>{t("release_notes_head", { version: APP_VERSION })}</span>
        <span className="text-[var(--ink-2)]">{APP_BUILD_DATE}</span>
        <span className="h-px flex-1 bg-[var(--border)]" />
      </div>
      {items.map((it) => (
        <div key={it.title} className="grid grid-cols-[36px_1fr] items-start gap-3">
          <span className="grid size-9 place-items-center rounded-[9px] border border-[var(--brand-primary-soft)] bg-[var(--surface)]/70 text-[var(--brand-primary)]">
            {it.icon}
          </span>
          <div className="flex flex-col gap-0.5 min-w-0">
            <span className="text-[13px] font-semibold text-[var(--ink-1)] tracking-[-0.005em]">
              {it.title}
            </span>
            <span className="text-[12px] leading-[1.45] text-[var(--ink-3)]">
              {it.desc}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function ServicesPanel() {
  const health = useSystemHealth();
  if (health.isLoading || !health.data) {
    return <div className="py-2 text-[12px] text-[var(--ink-3)]">…</div>;
  }
  return (
    <div className="flex flex-col gap-0.5 py-1">
      {health.data.services.map((svc) => (
        <ServiceRow key={svc.key} service={svc} />
      ))}
    </div>
  );
}

function ServiceRow({ service }: { service: ServiceStatus }) {
  const t = useTranslations("bank.settings");
  const isWarn =
    service.status === "degraded" ||
    service.status === "down" ||
    service.status === "not_implemented";
  const tileTone = isWarn
    ? "bg-[color-mix(in_srgb,var(--state-warn-fg)_12%,transparent)] text-[var(--state-warn-fg)]"
    : "bg-[color-mix(in_srgb,var(--state-ok-fg)_10%,transparent)] text-[var(--state-ok-fg)]";
  const statusText =
    service.status === "ok"
      ? t("service_status_ok")
      : service.status === "degraded"
        ? t("service_status_degraded")
        : service.status === "down"
          ? t("service_status_down")
          : t("service_status_not_implemented");
  const statusTone = isWarn
    ? "text-[var(--state-warn-fg)]"
    : "text-[var(--state-ok-fg)]";
  const nameKey = `service_${service.key}` as const;
  const name = t(nameKey);

  return (
    <div className="grid grid-cols-[36px_1fr_auto] items-center gap-3.5 rounded-md px-2.5 py-2.5 transition-colors hover:bg-[var(--surface-2)]">
      <div className={cn("grid size-8 place-items-center rounded-lg", tileTone)}>
        <ServiceIcon serviceKey={service.key} className="size-4" />
      </div>
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-[13px] font-medium tracking-[-0.005em] text-[var(--ink-1)]">
          {name}
        </span>
        {service.tip ? (
          <span className="text-[11.5px] leading-[1.4] text-[var(--ink-3)]">
            {service.tip}
          </span>
        ) : null}
      </div>
      <span className={cn("text-[11.5px] font-semibold", statusTone)}>{statusText}</span>
    </div>
  );
}

function ServiceIcon({
  serviceKey,
  className,
}: {
  serviceKey: string;
  className?: string;
}) {
  switch (serviceKey) {
    case "search":
      return <Search className={className} />;
    case "dossiers_db":
      return <Database className={className} />;
    case "soliq_import":
      return <FileText className={className} />;
    case "pdf_generation":
      return <FileSearch className={className} />;
    case "faktura_uz":
      return <AlertTriangle className={className} />;
    default:
      return <AlertTriangle className={className} />;
  }
}

function ServicesValueText() {
  const t = useTranslations("bank.settings");
  const health = useSystemHealth();
  if (!health.data) return <>…</>;
  const real = health.data.services.filter((s) => s.status !== "not_implemented");
  const hasDown = real.some((s) => s.status === "down");
  const hasDegraded = real.some((s) => s.status === "degraded");
  if (hasDown) return <>{t("services_value_down")}</>;
  if (hasDegraded) return <>{t("services_value_degraded")}</>;
  return <>{t("services_value_all_ok")}</>;
}

function FooterStrip() {
  const t = useTranslations("bank.settings");
  return (
    <div className="mt-2 flex items-center justify-between gap-3 border-t border-[var(--border)] bg-[var(--surface-2)] px-6 py-3.5 text-[12px] text-[var(--ink-3)]">
      <span>
        {t("support_label")} —{" "}
        <a
          href={`mailto:${t("support_email")}`}
          className="font-semibold text-[var(--ink-1)] no-underline"
          style={{ borderBottom: "1px solid var(--brand-primary)" }}
        >
          {t("support_email")}
        </a>
      </span>
      <span>{t("copyright_short")}</span>
    </div>
  );
}
