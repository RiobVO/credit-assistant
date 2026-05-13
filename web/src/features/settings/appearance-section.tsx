"use client";

import { Check } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

import {
  type Density,
  type FontScale,
  type Theme,
  useAppearance,
} from "./use-appearance";
import { useReducedMotion } from "@/lib/use-reduced-motion";

export function AppearanceSection() {
  const t = useTranslations("bank.settings");
  const { state, setTheme, setDensity, setFontScale, setReducedMotion } =
    useAppearance();
  const osPrefersReduced = useReducedMotion();

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-6">
      <Row
        title={t("ap_theme_title")}
        hint={t("ap_theme_hint")}
        control={<ThemeSwatches active={state.theme} onSelect={setTheme} />}
      />
      <Row
        title={t("ap_density_title")}
        hint={t("ap_density_hint")}
        control={
          <Segmented
            value={state.density}
            options={[
              { value: "compact", label: t("ap_density_compact") },
              { value: "standard", label: t("ap_density_standard") },
            ]}
            onSelect={(v) => setDensity(v as Density)}
          />
        }
      />
      <Row
        title={t("ap_font_title")}
        hint={t("ap_font_hint")}
        control={
          <Segmented
            value={state.fontScale}
            options={[
              { value: "s", label: t("ap_font_s") },
              { value: "m", label: t("ap_font_m") },
              { value: "l", label: t("ap_font_l") },
            ]}
            onSelect={(v) => setFontScale(v as FontScale)}
            variant="font"
          />
        }
      />
      <Row
        title={t("ap_motion_title")}
        hint={t("ap_motion_hint")}
        cue={
          osPrefersReduced ? t("ap_motion_os_reduced") : t("ap_motion_os_normal")
        }
        control={
          <Toggle
            checked={state.reducedMotion}
            onChange={(v) => setReducedMotion(v)}
            label={t("ap_motion_title")}
          />
        }
        last
      />
    </div>
  );
}

function Row({
  title,
  hint,
  cue,
  control,
  last,
}: {
  title: string;
  hint: string;
  cue?: string;
  control: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[1fr_auto] items-center gap-6 py-[18px]",
        !last && "border-b border-[var(--border)]",
      )}
    >
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-[13px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {title}
        </span>
        <span className="text-[12px] leading-[1.45] text-[var(--ink-3)] max-w-[56ch]">
          {hint}
        </span>
        {cue ? (
          <span className="mt-0.5 inline-flex items-center gap-1.5 text-[11px] font-medium text-[var(--state-ok-fg)]">
            <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
            {cue}
          </span>
        ) : null}
      </div>
      {control}
    </div>
  );
}

function ThemeSwatches({
  active,
  onSelect,
}: {
  active: Theme;
  onSelect: (t: Theme) => void;
}) {
  const t = useTranslations("bank.settings");
  return (
    <div className="flex gap-3.5">
      <Swatch
        variant="light"
        label={t("ap_theme_light")}
        active={active === "light"}
        onClick={() => onSelect("light")}
      />
      <Swatch variant="dark" label={t("ap_theme_dark")} disabled wipLabel={t("ap_theme_wip_sub")} />
      <Swatch variant="system" label={t("ap_theme_system")} disabled wipLabel={t("ap_theme_wip_sub")} />
    </div>
  );
}

function Swatch({
  variant,
  label,
  active,
  disabled,
  wipLabel,
  onClick,
}: {
  variant: "light" | "dark" | "system";
  label: string;
  active?: boolean;
  disabled?: boolean;
  wipLabel?: string;
  onClick?: () => void;
}) {
  const bg =
    variant === "light"
      ? "linear-gradient(135deg, #fff 0%, var(--surface-3) 100%)"
      : variant === "dark"
        ? "linear-gradient(135deg, #1a1d2e 0%, #0e1525 100%)"
        : "linear-gradient(90deg, #fff 0%, #fff 50%, #1a1d2e 50%, #0e1525 100%)";
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex flex-col items-center text-center",
        disabled ? "cursor-not-allowed" : "cursor-pointer",
      )}
    >
      <span
        className={cn(
          "relative h-14 w-20 overflow-hidden rounded-lg border-[1.5px] transition-all duration-200",
          active
            ? "border-[var(--brand-primary)] shadow-[0_0_0_3px_var(--brand-primary-ring)]"
            : "border-[var(--border)]",
          disabled ? "opacity-55" : "hover:-translate-y-px",
        )}
        style={{ background: bg }}
      >
        <span className="absolute inset-[9px] grid grid-rows-[6px_4px_4px] gap-1">
          <span
            style={{
              background:
                variant === "light"
                  ? "color-mix(in srgb, var(--ink-1) 18%, transparent)"
                  : variant === "dark"
                    ? "color-mix(in srgb, #fff 26%, transparent)"
                    : "linear-gradient(90deg, rgba(14,21,37,0.18) 50%, rgba(255,255,255,0.26) 50%)",
              borderRadius: 2,
            }}
          />
          <span
            style={{
              width: "70%",
              background:
                variant === "light"
                  ? "color-mix(in srgb, var(--ink-1) 10%, transparent)"
                  : variant === "dark"
                    ? "color-mix(in srgb, #fff 14%, transparent)"
                    : "linear-gradient(90deg, rgba(14,21,37,0.10) 50%, rgba(255,255,255,0.14) 50%)",
              borderRadius: 2,
            }}
          />
          <span
            style={{
              width: "50%",
              background:
                variant === "light"
                  ? "color-mix(in srgb, var(--ink-1) 10%, transparent)"
                  : variant === "dark"
                    ? "color-mix(in srgb, #fff 14%, transparent)"
                    : "linear-gradient(90deg, rgba(14,21,37,0.10) 50%, rgba(255,255,255,0.14) 50%)",
              borderRadius: 2,
            }}
          />
        </span>
        {active ? (
          <span className="absolute right-1.5 top-1.5 grid size-3.5 place-items-center rounded-full bg-[var(--brand-primary)] text-white">
            <Check className="size-2" strokeWidth={3} />
          </span>
        ) : null}
      </span>
      <span
        className={cn(
          "mt-1.5 text-[11.5px] leading-tight",
          active
            ? "font-semibold text-[var(--ink-1)]"
            : disabled
              ? "text-[var(--ink-4)]"
              : "text-[var(--ink-2)]",
        )}
      >
        {label}
        {wipLabel ? (
          <span className="mt-0.5 block text-[9.5px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-4)]">
            {wipLabel}
          </span>
        ) : null}
      </span>
    </button>
  );
}

function Segmented({
  value,
  options,
  onSelect,
  variant,
}: {
  value: string;
  options: Array<{ value: string; label: string }>;
  onSelect: (value: string) => void;
  variant?: "default" | "font";
}) {
  return (
    <div className="inline-flex gap-0 rounded-lg bg-[var(--surface-3)] p-[3px]">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(opt.value)}
            className={cn(
              "min-w-[42px] cursor-pointer rounded-md border-0 px-3.5 py-1.5 transition-all",
              active
                ? "bg-white font-semibold text-[var(--ink-1)] shadow-[0_1px_2px_rgba(15,23,42,0.08)]"
                : "bg-transparent font-medium text-[var(--ink-3)] hover:text-[var(--ink-1)]",
              variant !== "font" && "text-[12.5px]",
              variant === "font" && opt.value === "s" && "text-[11.5px]",
              variant === "font" && opt.value === "m" && "text-[12.5px]",
              variant === "font" && opt.value === "l" && "text-[13.5px]",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="relative inline-block h-5 w-9 flex-shrink-0">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
        aria-label={label}
      />
      <span
        className={cn(
          "absolute inset-0 cursor-pointer rounded-full transition-colors duration-180",
          checked ? "bg-[var(--brand-primary)] opacity-100" : "bg-[var(--ink-4)] opacity-50",
        )}
      >
        <span
          className={cn(
            "absolute left-0.5 top-0.5 size-4 rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.15)] transition-transform duration-180",
            checked ? "translate-x-4" : "translate-x-0",
          )}
        />
      </span>
    </label>
  );
}
