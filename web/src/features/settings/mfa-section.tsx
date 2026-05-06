"use client";

// 2FA card в Security секции /settings. Состояние computed из `analyst.mfa_enabled`
// (backend возвращает true когда analyst.mfa_secret != NULL).
//
// Disabled → CTA «Включить 2FA» → MfaEnrollModal
// Enabled  → status «Активна» + кнопка «Отключить» → MfaDisableModal

import { Shield, ShieldCheck, ShieldOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useAnalyst } from "@/lib/auth";

import { MfaDisableModal } from "./mfa-disable-modal";
import { MfaEnrollModal } from "./mfa-enroll-modal";

export function MfaSection() {
  const t = useTranslations("bank.settings");
  const { data: analyst } = useAnalyst();
  const [modal, setModal] = useState<"enroll" | "disable" | null>(null);

  if (!analyst) {
    return null;
  }

  const enabled = analyst.mfa_enabled === true;

  return (
    <>
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-7">
        <div className="flex items-start gap-4">
          <div
            className={`grid size-11 flex-shrink-0 place-items-center rounded-xl ${
              enabled
                ? "bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]"
                : "bg-[var(--surface-3)] text-[var(--ink-3)]"
            }`}
          >
            {enabled ? (
              <ShieldCheck className="size-5" />
            ) : (
              <Shield className="size-5" />
            )}
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <h3 className="m-0 text-[14.5px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
              {t("mfa_section_title")}
            </h3>
            <p className="m-0 text-[12.5px] leading-[1.5] text-[var(--ink-3)]">
              {t("mfa_section_hint")}
            </p>
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
          <div className="flex flex-col gap-0.5">
            <span
              className={`text-[12.5px] font-semibold ${
                enabled
                  ? "text-[var(--state-ok-fg)]"
                  : "text-[var(--ink-2)]"
              }`}
            >
              {enabled
                ? t("mfa_enabled_status")
                : t("mfa_disabled_status")}
            </span>
            <span className="text-[11.5px] leading-[1.45] text-[var(--ink-3)]">
              {enabled ? t("mfa_enabled_desc") : t("mfa_disabled_desc")}
            </span>
          </div>
          {enabled ? (
            <button
              type="button"
              onClick={() => setModal("disable")}
              className="inline-flex h-9 flex-shrink-0 items-center gap-1.5 rounded-md border border-[var(--border)] bg-white px-3 text-[12px] font-medium text-[var(--state-bad-fg)] transition-colors hover:bg-[color-mix(in_srgb,var(--state-bad-fg)_8%,white)]"
            >
              <ShieldOff className="size-3.5" />
              {t("mfa_disable_cta")}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setModal("enroll")}
              className="inline-flex h-9 flex-shrink-0 items-center gap-1.5 rounded-md bg-[var(--brand-primary)] px-3.5 text-[12.5px] font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)]"
            >
              <ShieldCheck className="size-3.5" />
              {t("mfa_enable_cta")}
            </button>
          )}
        </div>
      </div>

      {modal === "enroll" ? (
        <MfaEnrollModal onClose={() => setModal(null)} />
      ) : null}
      {modal === "disable" ? (
        <MfaDisableModal onClose={() => setModal(null)} />
      ) : null}
    </>
  );
}
