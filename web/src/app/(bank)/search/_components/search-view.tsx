"use client";

import {
  ArrowRight,
  Building,
  FileText,
  FileX,
  Info,
  Plus,
  Search as SearchIcon,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { rememberBackTarget } from "@/features/dossier/back-target";
import {
  type BorrowerSearchResult,
  scoreBand,
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

function validateInn(raw: string): { ok: true; value: string } | { ok: false; message: string } {
  const cleaned = raw.trim();
  if (!cleaned) return { ok: false, message: "Введите ИНН" };
  if (!/^\d+$/.test(cleaned)) return { ok: false, message: "Только цифры" };
  if (cleaned.length !== 9 && cleaned.length !== 14) {
    return { ok: false, message: "ИНН должен быть 9 или 14 цифр" };
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
  const [inn, setInn] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    rememberBackTarget("/search");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage post-mount load; init со SSR [] для избежания hydration-mismatch
    setRecent(loadRecent());
  }, []);

  const runSearch = async (raw: string) => {
    const v = validateInn(raw);
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
        message: err instanceof Error ? err.message : "Не удалось выполнить поиск",
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
    if (state.kind !== "idle" && state.kind !== "loading") {
      setState({ kind: "idle" });
    }
  };

  const handleChipClick = (chipInn: string) => {
    setInn(chipInn);
    void runSearch(chipInn);
  };

  const isValid = inn.length === 9 || inn.length === 14;
  const isLoading = state.kind === "loading";

  return (
    <>
      <BankPageHead
        title="Поиск компании"
        subtitle="Введите 9-значный ИНН узбекской компании, чтобы открыть кредитное досье и увидеть рекомендацию системы."
        actions={
          <Link
            href="/manual-input"
            className="inline-flex h-9 items-center gap-2 rounded-md bg-[var(--ub-accent)] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--ub-accent-hover)]"
          >
            <Plus className="size-3.5" />
            Новая заявка
          </Link>
        }
      />

      <form
        onSubmit={handleSubmit}
        className="mb-3 flex items-stretch gap-3"
        noValidate
      >
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[var(--ub-ink-4)]" />
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
              "h-[44px] w-full rounded-md border bg-[var(--ub-surface)] pr-9 pl-9 font-mono text-[15px] tracking-[0.04em] text-[var(--ub-ink)] outline-none transition-colors",
              "border-[var(--ub-hairline)] placeholder:text-[var(--ub-ink-4)]",
              "focus:border-[var(--ub-accent)] focus:shadow-[0_0_0_3px_var(--ub-accent-ring)]",
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
              aria-label="Очистить"
              className="absolute top-1/2 right-2 grid size-[22px] -translate-y-1/2 place-items-center rounded text-[var(--ub-ink-4)] hover:bg-[var(--ub-surface-2)] hover:text-[var(--ub-ink-2)]"
            >
              <X className="size-3.5" />
            </button>
          ) : null}
        </div>
        <button
          type="submit"
          disabled={!isValid || isLoading}
          className={cn(
            "inline-flex h-[44px] items-center justify-center rounded-md bg-[var(--ub-accent)] px-5 text-[15px] font-semibold text-white transition-colors",
            "hover:bg-[var(--ub-accent-hover)] disabled:cursor-not-allowed disabled:opacity-55",
          )}
        >
          {isLoading ? "Ищем…" : "Найти"}
        </button>
      </form>

      <HintRow
        recent={recent}
        onChipClick={handleChipClick}
        showHelper={state.kind === "idle"}
      />

      {state.kind === "error" ? (
        <ErrorState message={state.message} />
      ) : state.kind === "result" ? (
        <ResultStates result={state.data} inn={state.inn} />
      ) : state.kind === "idle" ? (
        <EmptyHero />
      ) : null}
    </>
  );
}

// ─────────────── Sub-views ───────────────

function HintRow({
  recent,
  onChipClick,
  showHelper,
}: {
  recent: string[];
  onChipClick: (inn: string) => void;
  showHelper: boolean;
}) {
  if (recent.length === 0 && !showHelper) return null;
  return (
    <div className="mb-8 flex flex-wrap items-center gap-3 text-[13px] text-[var(--ub-ink-3)]">
      {recent.length > 0 ? (
        <>
          <span className="text-[13px] text-[var(--ub-ink-3)]">Недавние:</span>
          {recent.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => onChipClick(r)}
              className="inline-flex items-center gap-1.5 rounded-full border border-[var(--ub-hairline)] bg-[var(--ub-surface-2)] px-2.5 py-1 font-mono text-[12px] text-[var(--ub-ink-2)] transition-colors hover:border-[#CBD5E1] hover:bg-[var(--ub-surface-3)] hover:text-[var(--ub-ink)]"
            >
              {formatInn(r)}
            </button>
          ))}
        </>
      ) : null}
      {showHelper ? (
        <span className="ml-auto inline-flex items-center gap-2 text-[12px] text-[var(--ub-ink-3)]">
          ИНН в Узбекистане — 9 цифр
          <kbd className="rounded border border-b-2 border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--ub-ink-2)]">
            Enter
          </kbd>
        </span>
      ) : null}
    </div>
  );
}

function EmptyHero() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-8 py-14 text-center">
      <div className="grid size-10 place-items-center rounded-md bg-[var(--ub-surface-3)] text-[var(--ub-ink-2)]">
        <Building className="size-5" />
      </div>
      <h3 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-[var(--ub-ink)]">
        Начните с ИНН
      </h3>
      <p className="m-0 max-w-[56ch] text-[14px] text-[var(--ub-ink-3)]">
        Введите идентификационный номер компании — система найдёт существующее
        досье или предложит загрузить выгрузки для нового заёмщика.
      </p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-[#FCA5A5] bg-[var(--ub-bad-bg)] px-5 py-4 text-[13.5px] text-[var(--ub-bad-fg)]"
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
  if (result.found && result.dossier_id) {
    return <FoundWithDossier result={result} inn={inn} />;
  }
  if (result.found) {
    return <NoDossierState inn={inn} name={result.borrower_name ?? "—"} />;
  }
  return <NotFoundState inn={inn} />;
}

function FoundWithDossier({
  result,
  inn,
}: {
  result: BorrowerSearchResult;
  inn: string;
}) {
  const band = scoreBand(result.display_score) ?? "warn";
  const colors: Record<"good" | "warn" | "bad", { fg: string; bg: string; line: string }> = {
    good: { fg: "var(--ub-ok-fg)", bg: "var(--ub-ok-bg)", line: "#059669" },
    warn: { fg: "var(--ub-warn-fg)", bg: "var(--ub-warn-bg)", line: "#D97706" },
    bad: { fg: "var(--ub-bad-fg)", bg: "var(--ub-bad-bg)", line: "#DC2626" },
  };
  const c = colors[band];

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--ub-hairline)] bg-[var(--ub-surface)]">
      <div className="grid gap-5 border-b border-[var(--ub-hairline)] p-6 md:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center gap-2 text-[13px] text-[var(--ub-ink-3)]">
            <Building className="size-3.5" />
            <span className="font-mono">{formatInn(inn)}</span>
            <span className="text-[var(--ub-hairline)]">·</span>
            <span
              className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[12px] font-medium"
              style={{ color: "var(--ub-ok-fg)", background: "var(--ub-ok-bg)" }}
            >
              <span
                className="size-1.5 rounded-full"
                style={{ background: "var(--ub-ok-fg)" }}
              />
              Досье найдено
            </span>
          </div>
          <h2 className="m-0 text-[22px] font-semibold tracking-[-0.015em] text-[var(--ub-ink)]">
            {result.borrower_name ?? "—"}
          </h2>
          {result.created_at ? (
            <p className="mt-1.5 text-[13px] text-[var(--ub-ink-3)]">
              Последнее досье обновлено{" "}
              {new Date(result.created_at).toLocaleDateString("ru", {
                day: "2-digit",
                month: "long",
                year: "numeric",
              })}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col items-end gap-1.5 md:min-w-[180px]">
          <span className="text-[11px] font-semibold tracking-[0.08em] text-[var(--ub-ink-3)] uppercase">
            Скоринг
          </span>
          <div className="font-semibold tabular-nums text-[36px] leading-none tracking-[-0.03em] text-[var(--ub-ink)]">
            {result.display_score ?? "—"}
            <span className="ml-1 text-[16px] font-medium text-[var(--ub-ink-3)]">
              / 100
            </span>
          </div>
          {result.display_score != null ? (
            <div className="block h-1.5 w-[180px] overflow-hidden rounded-full bg-[var(--ub-surface-3)]">
              <span
                className="block h-full rounded-full"
                style={{
                  width: `${result.display_score}%`,
                  background: c.line,
                }}
              />
            </div>
          ) : null}
        </div>
      </div>

      <div
        className="flex flex-wrap justify-end gap-3 p-4"
        style={{ background: "var(--ub-surface)" }}
      >
        <Link
          href={`/dossier/${result.dossier_id}`}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-3 text-[13px] font-medium text-[var(--ub-ink)] transition-colors hover:bg-[var(--ub-surface-2)]"
        >
          <FileText className="size-3.5" />
          Открыть полное досье
        </Link>
        <Link
          href={`/manual-input?inn=${encodeURIComponent(inn)}`}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-[var(--ub-accent)] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--ub-accent-hover)]"
        >
          Пересобрать с новыми данными
          <ArrowRight className="size-3.5" />
        </Link>
      </div>
    </div>
  );
}

function NoDossierState({ inn, name }: { inn: string; name: string }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-[var(--ub-hairline)] bg-[var(--ub-surface)] p-8">
      <div className="grid size-10 place-items-center rounded-md bg-[var(--ub-info-bg)] text-[var(--ub-info-fg)]">
        <Info className="size-5" />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-[var(--ub-ink)]">
          Компания найдена, но досье не сформировано
        </h3>
        <span
          className="rounded px-2 py-0.5 text-[12px] font-medium"
          style={{ color: "var(--ub-info-fg)", background: "var(--ub-info-bg)" }}
        >
          Новый клиент
        </span>
      </div>
      <div className="w-full rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface-2)] px-3.5 py-2.5">
        <div className="mb-0.5 text-[12px] text-[var(--ub-ink-3)]">
          Найдено в реестре
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[13px]">
          <span className="font-mono text-[var(--ub-ink)]">{formatInn(inn)}</span>
          <span className="text-[var(--ub-hairline)]">·</span>
          <span className="text-[var(--ub-ink)]">{name}</span>
        </div>
      </div>
      <p className="m-0 max-w-[56ch] text-[14px] text-[var(--ub-ink-3)]">
        Кредитное досье ещё не собрано. Запустите формирование — система пройдёт
        через 3 шага мастера и подготовит scoring.
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Link
          href={`/manual-input?inn=${encodeURIComponent(inn)}`}
          className="inline-flex h-8 items-center gap-1.5 rounded-md bg-[var(--ub-accent)] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--ub-accent-hover)]"
        >
          <Plus className="size-3.5" />
          Сформировать досье
        </Link>
      </div>
    </div>
  );
}

function NotFoundState({ inn }: { inn: string }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-[var(--ub-hairline)] bg-[var(--ub-surface)] p-8">
      <div className="grid size-10 place-items-center rounded-md bg-[var(--ub-warn-bg)] text-[var(--ub-warn-fg)]">
        <FileX className="size-5" />
      </div>
      <h3 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-[var(--ub-ink)]">
        Компания не найдена
      </h3>
      <p className="m-0 max-w-[56ch] text-[14px] text-[var(--ub-ink-3)]">
        ИНН <span className="font-mono text-[var(--ub-ink)]">{formatInn(inn)}</span>{" "}
        не встречался в системе. Проверьте правильность ввода или загрузите выгрузки
        Soliq — мы создадим новое досье с нуля.
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Link
          href={`/manual-input?inn=${encodeURIComponent(inn)}`}
          className="inline-flex h-8 items-center gap-1.5 rounded-md bg-[var(--ub-accent)] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--ub-accent-hover)]"
        >
          <Plus className="size-3.5" />
          Создать досье
        </Link>
      </div>
    </div>
  );
}
