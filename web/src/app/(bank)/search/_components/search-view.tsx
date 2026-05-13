"use client";

import {
  Building,
  FileX,
  Info,
  Plus,
  Search as SearchIcon,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";

import { LiveStrip } from "@/features/search/live-strip";
import { RecentChips } from "@/features/search/recent-chips";
import { ResultCard } from "@/features/search/result-card";
import { ShowcaseBar, type ShowcaseKind } from "@/features/search/showcase-bar";

// AmbientOrbs + GridPattern — pure decoration, не блокируют hero. Lazy-load
// с ssr:false → не уходят в initial JS bundle. Ускоряет навигацию между
// страницами (особенно в dev-mode где turbopack recompiles).
const AmbientOrbs = dynamic(
  () => import("@/features/search/ambient-orbs").then((m) => m.AmbientOrbs),
  { ssr: false },
);
const GridPattern = dynamic(
  () => import("@/features/search/grid-pattern").then((m) => m.GridPattern),
  { ssr: false },
);
import {
  type BorrowerSearchResult,
  searchBorrower,
} from "@/lib/bank-api";
import { cn } from "@/lib/utils";

const RECENT_KEY = "ca:bank-search-recent-inns";
const RECENT_MAX = 4;

// ─────────────── helpers ───────────────

function formatInn(inn: string): string {
  if (inn.length === 9) {
    return inn.replace(/(\d{3})(\d{3})(\d{3})/, "$1 $2 $3");
  }
  return inn;
}

function loadRecent(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as unknown;
    if (Array.isArray(arr)) {
      return arr.filter((v): v is string => typeof v === "string").slice(0, RECENT_MAX);
    }
  } catch {
    /* ignore */
  }
  return [];
}

function saveRecent(inn: string): void {
  if (typeof window === "undefined") return;
  const cur = loadRecent();
  const next = [inn, ...cur.filter((x) => x !== inn)].slice(0, RECENT_MAX);
  try {
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* localStorage full / disabled — silently skip */
  }
}

function validateInn(
  raw: string,
  msgs: { required: string; digitsOnly: string; length: string },
): { ok: true; value: string } | { ok: false; message: string } {
  const cleaned = raw.trim();
  if (!cleaned) return { ok: false, message: msgs.required };
  if (!/^\d+$/.test(cleaned)) return { ok: false, message: msgs.digitsOnly };
  if (cleaned.length !== 9 && cleaned.length !== 14) {
    return { ok: false, message: msgs.length };
  }
  return { ok: true, value: cleaned };
}

// ─────────────── State machine ───────────────

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "result"; data: BorrowerSearchResult; inn: string }
  | { kind: "error"; message: string };

// ─────────────── Main view ───────────────

export function SearchView() {
  const t = useTranslations("bank.search");
  const [inn, setInn] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });
  const [recent, setRecent] = useState<string[]>([]);
  const [showcase, setShowcase] = useState<ShowcaseKind | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage post-mount load
    setRecent(loadRecent());
  }, []);

  const runSearch = async (raw: string) => {
    const v = validateInn(raw, {
      required: t("error_required"),
      digitsOnly: t("error_digits_only"),
      length: t("error_length"),
    });
    if (!v.ok) {
      setState({ kind: "error", message: v.message });
      return;
    }
    setState({ kind: "loading" });
    try {
      const data = await searchBorrower(v.value);
      setState({ kind: "result", data, inn: v.value });
      saveRecent(v.value);
      setRecent(loadRecent());
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : t("error_generic"),
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void runSearch(inn);
  };

  const handleChange = (raw: string) => {
    const cleaned = raw.replace(/\D/g, "").slice(0, 14);
    setInn(cleaned);
    // Ручной ввод сбрасывает showcase-режим — пользователь делает свой поиск.
    if (showcase !== null) setShowcase(null);
    if (state.kind !== "idle" && state.kind !== "loading") {
      setState({ kind: "idle" });
    }
  };

  const handleChipClick = (chipInn: string) => {
    setInn(chipInn);
    void runSearch(chipInn);
  };

  const handleShowcase = (kind: ShowcaseKind, presetInn: string): void => {
    setShowcase(kind);
    if (kind === "idle") {
      setInn("");
      setState({ kind: "idle" });
      return;
    }
    // Реальный flow: подставляем ИНН + запускаем search → backend ответ +
    // все анимации (count-up, sparkline draw). Не mock data.
    setInn(presetInn);
    void runSearch(presetInn);
  };

  const isValid = inn.length === 9 || inn.length === 14;
  const isLoading = state.kind === "loading";

  // Active chip sparkline: sync на текущий result.card если ИНН совпадает.
  const activePoints =
    state.kind === "result" && state.inn === inn && state.data.card
      ? state.data.card.monthly_revenue_12m
      : null;

  return (
    <>
      {/* Page-level decorations — only on /search (showroom screen). */}
      <GridPattern />
      <AmbientOrbs />

      <div className="relative z-[1]">
        {/* Hero: title + sub + live-strip */}
        <header className="mb-7 animate-[rise_0.55s_cubic-bezier(0.16,0.84,0.44,1)_0.05s_both]">
          <h1 className="m-0 mb-[10px] text-[34px] leading-[1.08] font-semibold tracking-[-0.025em] text-[var(--ink-1)]">
            {t("title")}
          </h1>
          <p className="m-0 mb-[22px] max-w-[62ch] text-[15px] leading-[1.55] text-[var(--ink-3)] animate-[rise_0.55s_cubic-bezier(0.16,0.84,0.44,1)_0.12s_both]">
            {t("subtitle")}
          </p>
          <LiveStrip />
        </header>

        {/* Search form */}
        <form
          onSubmit={handleSubmit}
          className="mb-[14px] grid grid-cols-[1fr_auto] gap-[10px] animate-[rise_0.55s_cubic-bezier(0.16,0.84,0.44,1)_0.2s_both]"
          noValidate
        >
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-[18px] size-[18px] -translate-y-1/2 text-[var(--ink-3)] transition-colors" />
            <input
              type="text"
              inputMode="numeric"
              autoFocus
              placeholder="000 000 000"
              value={inn}
              onChange={(e) => handleChange(e.target.value)}
              disabled={isLoading}
              maxLength={14}
              className={cn(
                "h-[56px] w-full rounded-[12px] border-[1.5px] bg-[var(--surface)] pr-[50px] pl-[50px] font-mono text-[16px] tracking-[0.04em] text-[var(--ink-1)] outline-none transition-all",
                "border-[var(--border)] placeholder:text-[var(--ink-4)]",
                "focus:border-[var(--ink-1)] focus:shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_0_0_5px_rgba(14,21,37,0.08)]",
                "disabled:cursor-wait disabled:opacity-60",
              )}
            />
            {inn ? (
              <button
                type="button"
                onClick={() => {
                  setInn("");
                  setState({ kind: "idle" });
                }}
                aria-label={t("clear_aria")}
                className="absolute top-1/2 right-[14px] grid size-6 -translate-y-1/2 place-items-center rounded-md text-[var(--ink-4)] hover:bg-[var(--surface-3)] hover:text-[var(--ink-2)]"
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>
          <button
            type="submit"
            disabled={!isValid || isLoading}
            className={cn(
              "inline-flex h-[56px] items-center gap-[9px] rounded-[12px] bg-[var(--brand-primary)] px-[26px] text-[14px] font-semibold text-white shadow-[0_1px_0_rgba(255,255,255,0.1)_inset,0_10px_22px_-10px_color-mix(in_oklab,var(--brand-primary)_55%,transparent)] transition-all",
              "hover:-translate-y-px hover:bg-[var(--brand-primary-hover)] hover:shadow-[0_1px_0_rgba(255,255,255,0.12)_inset,0_14px_28px_-10px_color-mix(in_oklab,var(--brand-primary)_70%,transparent)] disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-45 disabled:shadow-none",
            )}
          >
            {isLoading ? t("submit_loading") : t("submit")}
          </button>
        </form>

        {/* Recent chips with active-spark synced на текущий result */}
        <RecentChips
          recent={recent}
          activeInn={inn}
          activePoints={activePoints}
          onChipClick={handleChipClick}
        />

        {state.kind === "error" ? (
          <ErrorState message={state.message} />
        ) : state.kind === "result" ? (
          <ResultStates result={state.data} inn={state.inn} />
        ) : state.kind === "idle" ? (
          <EmptyHero />
        ) : null}
      </div>

      {/* Showcase-bar — быстрое переключение состояний для demo / QA. */}
      <ShowcaseBar active={showcase} onPick={handleShowcase} />
    </>
  );
}

// ─────────────── Sub-views ───────────────

function EmptyHero() {
  const t = useTranslations("bank.search");
  return (
    <div className="relative overflow-hidden rounded-[16px] border border-[var(--border)] bg-[var(--surface)] px-7 py-12 text-center shadow-[0_1px_0_rgba(255,255,255,0.8)_inset,0_14px_36px_-24px_rgba(14,21,37,0.08)] animate-[rise-card_0.6s_cubic-bezier(0.16,0.84,0.44,1)_both]">
      <div
        aria-hidden
        className="pointer-events-none absolute top-[-80px] left-1/2 h-[280px] w-[460px] -translate-x-1/2"
        style={{
          background:
            "radial-gradient(closest-side, color-mix(in oklab, var(--brand-primary) 9%, transparent) 0%, transparent 72%)",
          animation: "ds-orb-drift-a 24s ease-in-out infinite",
        }}
      />
      <div
        className="relative z-[1] mx-auto mb-4 grid size-[52px] place-items-center rounded-[14px] border text-[var(--brand-primary-ink)] shadow-[0_8px_22px_-12px_color-mix(in_oklab,var(--brand-primary)_40%,transparent)]"
        style={{
          background:
            "linear-gradient(135deg, var(--brand-primary-soft) 0%, color-mix(in oklab, var(--brand-primary) 18%, white) 100%)",
          borderColor: "color-mix(in oklab, var(--brand-primary) 16%, transparent)",
        }}
      >
        <Building className="size-[24px]" strokeWidth={1.7} />
      </div>
      <h3 className="relative z-[1] m-0 mb-2 text-[18px] font-semibold tracking-[-0.015em] text-[var(--ink-1)]">
        {t("empty_hero_title")}
      </h3>
      <p className="relative z-[1] m-0 mx-auto mb-4 max-w-[54ch] text-[13.5px] leading-[1.6] text-[var(--ink-3)]">
        {t("empty_hero_text")}
      </p>
      <div className="relative z-[1] inline-flex gap-3 text-[11.5px] text-[var(--ink-3)]">
        <span className="inline-flex items-center gap-1.5">
          {t("empty_hero_ex_prefix")}{" "}
          <code className="rounded-[5px] bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--ink-1)]">
            201 308 534
          </code>
        </span>
        <span style={{ color: "var(--border-strong)" }}>·</span>
        <span className="inline-flex items-center gap-1.5">
          {t("empty_hero_ex_or")}{" "}
          <code className="rounded-[5px] bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--ink-1)]">
            123 321 123
          </code>
        </span>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] px-5 py-4 text-[13.5px] text-[var(--state-bad-fg)]"
    >
      {message}
    </div>
  );
}

function ResultStates({
  result,
  inn,
}: {
  result: BorrowerSearchResult;
  inn: string;
}) {
  if (result.found && result.dossier_id && result.card) {
    return <ResultCard result={result} inn={inn} card={result.card} />;
  }
  if (result.found) {
    return <NoDossierState inn={inn} name={result.borrower_name ?? "—"} />;
  }
  return <NotFoundState inn={inn} />;
}

function NoDossierState({ inn, name }: { inn: string; name: string }) {
  const t = useTranslations("bank.search");
  return (
    <div className="flex flex-col items-start gap-3 rounded-[16px] border border-[var(--border)] bg-[var(--surface)] p-7 animate-[rise-card_0.6s_cubic-bezier(0.16,0.84,0.44,1)_both]">
      <div className="grid size-11 place-items-center rounded-[12px] bg-[var(--state-info-bg)] text-[var(--state-info-fg)]">
        <Info className="size-5" />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="m-0 text-[18px] font-semibold tracking-[-0.015em] text-[var(--ink-1)]">
          {t("no_dossier_title")}
        </h3>
        <span
          className="rounded-full px-2.5 py-0.5 text-[12px] font-medium"
          style={{ color: "var(--state-info-fg)", background: "var(--state-info-bg)" }}
        >
          {t("no_dossier_new_client")}
        </span>
      </div>
      <div className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3.5 py-2.5">
        <div className="mb-0.5 text-[12px] text-[var(--ink-3)]">
          {t("no_dossier_registry_found")}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[13px]">
          <span className="font-mono text-[var(--ink-1)]">{formatInn(inn)}</span>
          <span className="text-[var(--border-strong)]">·</span>
          <span className="text-[var(--ink-1)]">{name}</span>
        </div>
      </div>
      <p className="m-0 max-w-[56ch] text-[13.5px] text-[var(--ink-3)]">
        {t("no_dossier_text")}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Link
          href={`/manual-input?inn=${encodeURIComponent(inn)}`}
          className="inline-flex h-9 items-center gap-1.5 rounded-[9px] bg-[var(--brand-primary)] px-3 text-[13px] font-semibold text-white shadow-[0_6px_16px_-8px_color-mix(in_oklab,var(--brand-primary)_55%,transparent)] transition-all hover:-translate-y-px hover:bg-[var(--brand-primary-hover)]"
        >
          <Plus className="size-3.5" />
          {t("no_dossier_submit")}
        </Link>
      </div>
    </div>
  );
}

function NotFoundState({ inn }: { inn: string }) {
  const t = useTranslations("bank.search");
  return (
    <div className="relative flex flex-col items-start gap-3 overflow-hidden rounded-[16px] border border-[var(--border)] bg-[var(--surface)] p-7 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset,0_12px_30px_-22px_rgba(14,21,37,0.1)] animate-[rise-card_0.6s_cubic-bezier(0.16,0.84,0.44,1)_both]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(520px 180px at 0% 0%, color-mix(in oklab, var(--state-warn-fg) 6%, transparent) 0%, transparent 72%)",
        }}
      />
      <div className="relative z-[1] grid size-11 place-items-center rounded-[12px] border bg-[var(--state-warn-bg)] text-[var(--state-warn-fg)] border-[var(--state-warn-border)]">
        <FileX className="size-5" />
      </div>
      <h3 className="relative z-[1] m-0 text-[18px] font-semibold tracking-[-0.015em] text-[var(--ink-1)]">
        {t("not_found_title")}
      </h3>
      <p className="relative z-[1] m-0 max-w-[58ch] text-[13.5px] leading-[1.55] text-[var(--ink-3)]">
        <span className="rounded-[4px] bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-[13px] text-[var(--ink-1)]">
          {formatInn(inn)}
        </span>{" "}
        {t("not_found_text")}
      </p>
      <div className="relative z-[1] mt-2 flex flex-wrap gap-2">
        <Link
          href={`/manual-input?inn=${encodeURIComponent(inn)}`}
          className="inline-flex h-9 items-center gap-1.5 rounded-[9px] bg-[var(--brand-primary)] px-3.5 text-[13px] font-semibold text-white shadow-[0_6px_16px_-8px_color-mix(in_oklab,var(--brand-primary)_55%,transparent)] transition-all hover:-translate-y-px hover:bg-[var(--brand-primary-hover)]"
        >
          <Plus className="size-3.5" />
          {t("not_found_submit")}
        </Link>
      </div>
    </div>
  );
}
