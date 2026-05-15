"use client";

import { ChevronRight, Info, Palette, Shield, User } from "lucide-react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { AboutSection } from "@/features/settings/about-section";
import { AppearanceSection } from "@/features/settings/appearance-section";
import { ProfileSection } from "@/features/settings/profile-section";
import { SecuritySection } from "@/features/settings/security-section";
import { cn } from "@/lib/utils";

// Lazy decoration: grid-pattern не в initial bundle (Phase 3/4 pattern).
const GridPattern = dynamic(
  () => import("@/features/search/grid-pattern").then((m) => m.GridPattern),
  { ssr: false },
);

type Section = "profile" | "appearance" | "security" | "about";

const SECTIONS: Array<{
  key: Section;
  labelKey: "nav_profile" | "nav_appearance" | "nav_security" | "nav_about";
  Icon: React.ComponentType<{ className?: string }>;
}> = [
  { key: "profile", labelKey: "nav_profile", Icon: User },
  { key: "appearance", labelKey: "nav_appearance", Icon: Palette },
  { key: "security", labelKey: "nav_security", Icon: Shield },
  { key: "about", labelKey: "nav_about", Icon: Info },
];

export function SettingsView() {
  const t = useTranslations("bank.settings");
  const [section, setSection] = useState<Section>("profile");

  return (
    <>
      <GridPattern tone="default" />
      <div className="relative z-[1]">
        <BankPageHead
          title={t("title")}
          subtitle={t("subtitle")}
          actions={<SessionPill />}
        />
        <div className="grid gap-7 md:grid-cols-[220px_1fr]">
          <SettingsNav active={section} onChange={setSection} />
          <div>
            {section === "profile" ? <ProfileSection /> : null}
            {section === "appearance" ? <AppearanceSection /> : null}
            {section === "security" ? <SecuritySection /> : null}
            {section === "about" ? <AboutSection /> : null}
          </div>
        </div>
      </div>
    </>
  );
}

function SessionPill() {
  const t = useTranslations("bank.settings");
  // Время сессии: момент монтирования компонента ≈ когда analyst открыл страницу.
  // Real-стартовое время сессии = iat в JWT, но client его не видит (httpOnly).
  // Этого достаточно для UI-cue «активная сессия начата примерно в N».
  const when = new Date().toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tashkent",
  });
  return (
    <span
      className="inline-flex items-center gap-3.5 rounded-full border border-[var(--border)] bg-[var(--surface)]/70 px-3.5 py-2.5 text-[11.5px]"
      style={{ backdropFilter: "blur(8px)" }}
    >
      <span className="inline-flex items-center gap-1.5 text-[var(--ink-2)]">
        <span className="ds-pulse-ok size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
        <strong className="font-semibold text-[var(--ink-1)]">
          {t("session_active")}
        </strong>
      </span>
      <span className="border-l border-[var(--border)] pl-3.5 text-[var(--ink-2)]">
        {t("last_login", { when })}
      </span>
    </span>
  );
}

function SettingsNav({
  active,
  onChange,
}: {
  active: Section;
  onChange: (s: Section) => void;
}) {
  const t = useTranslations("bank.settings");
  return (
    <nav className="flex flex-col gap-1 pt-1.5">
      {SECTIONS.map((s) => {
        const Ico = s.Icon;
        const itemActive = s.key === active;
        return (
          <button
            key={s.key}
            type="button"
            onClick={() => onChange(s.key)}
            className={cn(
              "group relative grid cursor-pointer grid-cols-[32px_1fr_14px] items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-left transition-colors duration-160",
              itemActive
                ? "bg-[var(--surface)] shadow-[0_1px_1px_rgba(15,23,42,0.04)]"
                : "hover:bg-[var(--surface)]",
            )}
          >
            <span
              className={cn(
                "grid size-8 place-items-center rounded-lg transition-all duration-160",
                itemActive
                  ? "bg-[var(--brand-primary-soft)] text-[var(--brand-primary)]"
                  : "bg-[var(--surface-3)] text-[var(--ink-3)] group-hover:bg-[var(--brand-primary-soft)] group-hover:text-[var(--brand-primary)] group-hover:scale-105",
              )}
              style={{
                transitionTimingFunction:
                  "cubic-bezier(0.34, 1.56, 0.64, 1)",
              }}
            >
              <Ico className="size-4" />
            </span>
            <span
              className={cn(
                "text-[13px]",
                itemActive
                  ? "font-semibold text-[var(--ink-1)]"
                  : "font-medium text-[var(--ink-2)]",
              )}
            >
              {t(s.labelKey)}
            </span>
            <ChevronRight
              className={cn(
                "size-3.5 transition-all duration-220",
                itemActive
                  ? "translate-x-0 text-[var(--brand-primary)] opacity-100"
                  : "-translate-x-1 text-[var(--ink-4)] opacity-0 group-hover:translate-x-0 group-hover:opacity-60",
              )}
            />
            {itemActive ? (
              <span
                className="pointer-events-none absolute top-2 bottom-2 left-[-1px] w-0.5 rounded-[2px] bg-[var(--brand-primary)]"
                aria-hidden
              />
            ) : null}
          </button>
        );
      })}
      <div className="mt-2 px-2.5 text-[9.5px] font-bold uppercase tracking-[0.1em] text-[var(--ink-4)]">
        {t("nav_access_eyebrow")}
      </div>
      <div className="px-2.5 text-[11.5px] leading-[1.5] text-[var(--ink-4)]">
        {t("nav_access_hint")}
      </div>
    </nav>
  );
}
