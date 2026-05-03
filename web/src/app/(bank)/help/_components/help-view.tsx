"use client";

import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  Mail,
  MessageCircle,
  Phone,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { cn } from "@/lib/utils";

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

export function HelpView() {
  const t = useTranslations("bank.help");

  return (
    <>
      <BankPageHead title={t("title")} subtitle={t("subtitle")} />

      <div className="grid gap-6 md:grid-cols-[1fr_300px]">
        <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)]">
          <header className="border-b border-[var(--border)] px-6 py-4">
            <h2 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-[var(--ink-1)]">
              {t("faq_heading")}
            </h2>
          </header>
          <div className="divide-y divide-[var(--border)]">
            {FAQ_IDS.map((id) => (
              <FaqRow key={id} id={id} />
            ))}
          </div>
        </section>

        <aside className="flex flex-col gap-4">
          <ContactCard
            icon={<Mail className="size-4" />}
            title={t("contact_email")}
            value="ops@uzbekbank.uz"
            href="mailto:ops@uzbekbank.uz"
          />
          <ContactCard
            icon={<MessageCircle className="size-4" />}
            title={t("contact_slack")}
            value="#credit-assistant"
            hint={t("contact_slack_hint")}
          />
          <ContactCard
            icon={<Phone className="size-4" />}
            title={t("contact_hotline")}
            value="+998 71 200-00-00"
            hint={t("contact_hotline_hint")}
          />
          <ContactCard
            icon={<BookOpen className="size-4" />}
            title={t("contact_docs")}
            value="docs.credit-assistant"
            hint={t("contact_docs_hint")}
          />
          <div className="rounded-lg border border-[#F1D9A6] bg-[#FFF6E5] p-4 text-[13px] text-[var(--state-warn-fg)]">
            <div className="mb-1 inline-flex items-center gap-1.5 font-semibold">
              <AlertTriangle className="size-3.5" />
              {t("incident_title")}
            </div>
            <div className="text-[12.5px] leading-[1.45]">
              {t("incident_text")}
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}

function FaqRow({ id }: { id: FaqId }) {
  const t = useTranslations("bank.help");
  const [open, setOpen] = useState(false);
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
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left text-[14px] font-medium text-[var(--ink-1)] transition-colors hover:bg-[var(--surface-2)]"
      >
        {t(`faq_${id}_q`)}
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-[var(--ink-3)] transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      {open ? (
        <div className="px-6 pb-5 text-[13.5px] leading-[1.55] text-[var(--ink-2)]">
          {answer}
        </div>
      ) : null}
    </div>
  );
}

function ContactCard({
  icon,
  title,
  value,
  href,
  hint,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  href?: string;
  hint?: string;
}) {
  const inner = (
    <>
      <div className="mb-2 inline-flex items-center gap-2 text-[12px] font-medium text-[var(--ink-3)]">
        <span className="text-[var(--brand-primary)]">{icon}</span>
        {title}
      </div>
      <div className="text-[14px] font-semibold text-[var(--ink-1)]">{value}</div>
      {hint ? (
        <div className="mt-1 text-[12px] text-[var(--ink-3)]">{hint}</div>
      ) : null}
    </>
  );
  if (href) {
    return (
      <a
        href={href}
        className="block rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--brand-primary-soft)]"
      >
        {inner}
      </a>
    );
  }
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      {inner}
    </div>
  );
}
