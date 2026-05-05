"use client";

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  ChevronDown,
  Clock,
  Database,
  FileSpreadsheet,
  LifeBuoy,
  Mail,
  MessageSquare,
  Phone,
  RotateCcw,
  ScrollText,
} from "lucide-react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { cn } from "@/lib/utils";

import { getHotlineStatus, type HotlineStatus } from "@/features/help/business-hours";

const GridPattern = dynamic(
  () => import("@/features/search/grid-pattern").then((m) => m.GridPattern),
  { ssr: false },
);

const HOTLINE_PHONE = "+998 71 200-00-00";
const HOTLINE_TEL = "tel:+998712000000";
const SUPPORT_EMAIL = "ops@uzbekbank.uz";
const SLACK_CHANNEL = "#credit-assistant";
const DOCS_URL = "https://docs.credit-assistant";
const DOCS_LABEL = "docs.credit-assistant";

type FaqId =
  | "scoring"
  | "red_flags"
  | "insufficient"
  | "xltx"
  | "rebuild"
  | "audit"
  | "support";

const FAQ_IDS: FaqId[] = [
  "scoring",
  "red_flags",
  "insufficient",
  "xltx",
  "rebuild",
  "audit",
  "support",
];

const FAQ_ICONS: Record<FaqId, typeof BarChart3> = {
  scoring: BarChart3,
  red_flags: AlertTriangle,
  insufficient: Database,
  xltx: FileSpreadsheet,
  rebuild: RotateCcw,
  audit: ScrollText,
  support: LifeBuoy,
};

export function HelpView() {
  const t = useTranslations("bank.help");

  return (
    <>
      <GridPattern tone="default" />
      <div className="relative z-[1]">
        <BankPageHead
          title={t("title")}
          subtitle={t("subtitle")}
          actions={<StatusCard />}
        />

        <IncidentBand />

        <div className="grid gap-6 md:grid-cols-[1fr_340px]">
          <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
            <header className="flex items-baseline justify-between border-b border-[var(--border)] bg-gradient-to-b from-[var(--surface)] to-[var(--surface-2)] px-5 py-4">
              <h2 className="m-0 text-[14px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
                {t("faq_heading")}
              </h2>
              <span className="text-[11.5px] font-medium uppercase tracking-[0.08em] text-[var(--ink-4)]">
                {t("faq_topics", { n: FAQ_IDS.length })}
              </span>
            </header>
            <div>
              {FAQ_IDS.map((id, idx) => (
                <FaqRow key={id} id={id} defaultOpen={idx === 0} />
              ))}
            </div>
          </section>

          <ContactStack />
        </div>
      </div>
    </>
  );
}

function StatusCard() {
  const t = useTranslations("bank.help");
  return (
    <div className="inline-flex items-center gap-3 rounded-full border border-[var(--border)] bg-[var(--surface)]/70 px-3.5 py-2 backdrop-blur">
      <span className="inline-flex items-center gap-1.5 text-[11.5px] text-[var(--ink-2)]">
        <span
          aria-hidden
          className="pulse-ring-ok size-1.5 rounded-full bg-[var(--state-ok-fg)]"
        />
        <span>{t("status_api_label")}</span>
        <strong className="font-semibold text-[var(--ink-1)]">
          {t("status_api_version")}
        </strong>
      </span>
      <span className="inline-flex items-center gap-1.5 border-l border-[var(--border)] pl-3 text-[11.5px] text-[var(--ink-2)]">
        <span>{t("status_updated_label")}</span>
        <strong className="font-semibold text-[var(--ink-1)]">
          {t("status_updated_date")}
        </strong>
      </span>
    </div>
  );
}

function IncidentBand() {
  const t = useTranslations("bank.help");
  return (
    <div className="mb-6 flex items-center gap-3.5 rounded-xl border border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] p-3.5 pr-4">
      <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-[color:color-mix(in_srgb,var(--state-bad-fg)_10%,transparent)] text-[var(--state-bad-fg)]">
        <AlertTriangle className="size-4" strokeWidth={2.2} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="text-[13px] font-bold text-[var(--state-bad-fg)]">
          {t("incident_title")}
        </div>
        <div className="text-[12.5px] leading-snug text-[color:color-mix(in_srgb,var(--state-bad-fg)_85%,var(--ink-1))]">
          {t("incident_text")}
        </div>
      </div>
      <a
        href={HOTLINE_TEL}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-[var(--state-bad-fg)] px-3 py-1.5 text-[12.5px] font-semibold text-white transition-opacity hover:opacity-90"
      >
        <Phone className="size-3.5" />
        {t("incident_cta")}
      </a>
    </div>
  );
}

function FaqRow({ id, defaultOpen }: { id: FaqId; defaultOpen?: boolean }) {
  const t = useTranslations("bank.help");
  const [open, setOpen] = useState(defaultOpen ?? false);
  const Icon = FAQ_ICONS[id];

  const answer: ReactNode = t.rich(`faq_${id}_a`, {
    b: (chunks) => <b>{chunks}</b>,
    code: (chunks) => <code>{chunks}</code>,
    good: (chunks) => (
      <b style={{ color: "var(--state-ok-fg)" }}>{chunks}</b>
    ),
    warn: (chunks) => (
      <b style={{ color: "var(--state-warn-fg)" }}>{chunks}</b>
    ),
    bad: (chunks) => (
      <b style={{ color: "var(--state-bad-fg)" }}>{chunks}</b>
    ),
  });

  return (
    <div className="border-b border-[var(--border)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={cn(
          "grid w-full grid-cols-[44px_1fr_auto] items-start gap-3.5 px-5 py-3.5 text-left transition-colors",
          "hover:bg-[var(--surface-2)]",
          open && "bg-[var(--surface-2)]",
        )}
      >
        <span
          className={cn(
            "grid size-8 place-items-center rounded-[9px] bg-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)] transition-transform",
            "group-hover:scale-105",
          )}
        >
          <Icon className="size-4" />
        </span>
        <span className="pt-1.5">
          <span className="mb-0.5 block text-[10.5px] font-medium uppercase tracking-[0.06em] text-[var(--ink-4)]">
            {t(`faq_cat_${id}`)}
          </span>
          <span className="block text-[14px] font-medium leading-snug text-[var(--ink-1)]">
            {t(`faq_${id}_q`)}
          </span>
        </span>
        <ChevronDown
          className={cn(
            "mt-2 size-4 shrink-0 text-[var(--ink-3)] transition-transform duration-200",
            open && "rotate-180 text-[var(--brand-primary)]",
          )}
        />
      </button>
      {open ? (
        <div className="pl-[64px] pr-5 pb-4">
          <div
            className="rounded-r-lg border-l-2 border-[var(--brand-primary)] bg-gradient-to-r from-[var(--brand-primary-soft)] to-transparent py-2.5 pl-3.5 pr-5 text-[13.5px] leading-[1.6] text-[var(--ink-2)] [&_code]:rounded [&_code]:bg-[var(--surface-3)] [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[12px] [&_code]:text-[var(--ink-1)] [&_p]:m-0 [&_p:not(:last-child)]:mb-2"
          >
            {answer}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ContactStack() {
  const t = useTranslations("bank.help");
  return (
    <aside className="flex flex-col gap-3.5">
      <div className="px-1 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-4)]">
        {t("contacts_heading")}
      </div>

      <HotlinePrimaryCard />

      <a
        href={`https://uzbekbank.slack.com/channels/${SLACK_CHANNEL.slice(1)}`}
        className="group flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--brand-primary-soft)]"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-[var(--surface-3)] text-[var(--ink-2)] transition-colors group-hover:bg-[var(--brand-primary-soft)] group-hover:text-[var(--brand-primary-ink)]">
          <MessageSquare className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--ink-4)]">
            {t("contact_slack")}
          </div>
          <div className="text-[14px] font-semibold leading-tight text-[var(--ink-1)]">
            {SLACK_CHANNEL}
          </div>
          <div className="mt-0.5 text-[11.5px] text-[var(--ink-3)]">
            {t("contact_slack_hint")}
          </div>
        </div>
      </a>

      <a
        href={`mailto:${SUPPORT_EMAIL}`}
        className="group flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--brand-primary-soft)]"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-[var(--surface-3)] text-[var(--ink-2)] transition-colors group-hover:bg-[var(--brand-primary-soft)] group-hover:text-[var(--brand-primary-ink)]">
          <Mail className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--ink-4)]">
            {t("contact_email")}
          </div>
          <div className="text-[14px] font-semibold leading-tight text-[var(--ink-1)]">
            {SUPPORT_EMAIL}
          </div>
          <div className="mt-0.5 text-[11.5px] text-[var(--ink-3)]">
            {t("contact_email_hint")}
          </div>
        </div>
      </a>

      <a
        href={DOCS_URL}
        className="group mt-0.5 flex items-center gap-2.5 border-t border-dashed border-[var(--border)] px-1 pt-3.5 text-[var(--ink-2)] transition-colors hover:text-[var(--brand-primary)]"
      >
        <div className="flex-1">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--ink-4)]">
            {t("contact_docs")}
          </div>
          <div className="text-[13px] font-medium">{DOCS_LABEL}</div>
        </div>
        <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
      </a>

      <div className="mt-1 inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-[11.5px] text-[var(--ink-4)]">
        <Clock className="size-3.5 shrink-0" />
        {t("sla_note")}
      </div>
    </aside>
  );
}

function HotlinePrimaryCard() {
  const t = useTranslations("bank.help");
  const [status, setStatus] = useState<HotlineStatus | null>(null);

  useEffect(() => {
    const update = () => setStatus(getHotlineStatus(new Date()));
    const tId = setTimeout(update, 0);
    const iId = setInterval(update, 60_000);
    return () => {
      clearTimeout(tId);
      clearInterval(iId);
    };
  }, []);

  return (
    <a
      href={HOTLINE_TEL}
      className="group relative block overflow-hidden rounded-2xl border border-[var(--brand-primary-soft)] bg-gradient-to-b from-[var(--brand-primary-soft)] to-[var(--surface)] p-[18px] transition-all hover:-translate-y-px hover:shadow-[0_14px_36px_-16px_var(--brand-primary-ring)]"
    >
      <div className="mb-2 inline-flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[var(--brand-primary-ink)]">
        <Phone className="size-3" />
        {t("contact_hotline")}
      </div>
      <div className="mb-1.5 font-mono text-[18px] font-semibold tracking-[-0.01em] text-[var(--ink-1)] [font-variant-numeric:tabular-nums]">
        {HOTLINE_PHONE}
      </div>
      {status ? (
        status.open ? (
          <div className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[var(--state-ok-fg)]">
            <span
              aria-hidden
              className="pulse-ring-ok size-1.5 rounded-full bg-[var(--state-ok-fg)]"
            />
            {t("contact_hotline_status_open", { hour: status.untilHour })}
          </div>
        ) : (
          <div className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[var(--ink-3)]">
            <span
              aria-hidden
              className="size-1.5 rounded-full bg-[var(--ink-4)]"
            />
            {t("contact_hotline_status_closed", { hour: status.opensAtHour })}
          </div>
        )
      ) : null}
      <div className="mt-1.5 text-[11.5px] leading-snug text-[var(--ink-3)]">
        {t("contact_hotline_hours_note")}
      </div>
    </a>
  );
}
