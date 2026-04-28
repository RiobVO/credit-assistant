"use client";

import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { rememberBackTarget } from "@/features/dossier/back-target";
import { searchBorrower, type BorrowerSearchResult } from "@/lib/bank-api";
import { cn } from "@/lib/utils";

import { SearchResult } from "./search-result";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "result"; data: BorrowerSearchResult; inn: string }
  | { kind: "error"; message: string };

const INN_VALID_LENGTHS = [9, 14] as const;

function validateInn(raw: string): { ok: true; value: string } | { ok: false; message: string } {
  const cleaned = raw.trim();
  if (!cleaned) return { ok: false, message: "Введите ИНН" };
  if (!/^\d+$/.test(cleaned)) {
    return { ok: false, message: "ИНН содержит только цифры" };
  }
  if (!INN_VALID_LENGTHS.includes(cleaned.length as 9 | 14)) {
    return { ok: false, message: "ИНН должен быть 9 или 14 цифр" };
  }
  return { ok: true, value: cleaned };
}

export function SearchForm() {
  const [inn, setInn] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  // CA-055: запоминаем как back-target для досье — поиск → открыть досье →
  // «Назад» вернёт сюда, а не на /manual-input (если у пользователя был
  // submit где-то ранее в стеке).
  useEffect(() => {
    rememberBackTarget("/search");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const v = validateInn(inn);
    if (!v.ok) {
      setState({ kind: "error", message: v.message });
      return;
    }
    setState({ kind: "loading" });
    try {
      const data = await searchBorrower(v.value);
      setState({ kind: "result", data, inn: v.value });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Не удалось выполнить поиск",
      });
    }
  };

  const isLoading = state.kind === "loading";

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-[var(--ca-line)] bg-white p-6 shadow-sm"
        noValidate
      >
        <label
          htmlFor="inn"
          className="mb-2 block text-[12.5px] font-medium text-[var(--ca-text-strong)]"
        >
          ИНН заёмщика
        </label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[var(--ca-text-muted)]" />
            <input
              id="inn"
              type="text"
              inputMode="numeric"
              autoFocus
              placeholder="305012345 или 14-значный"
              value={inn}
              onChange={(e) => {
                setInn(e.target.value);
                if (state.kind === "error" || state.kind === "result") {
                  setState({ kind: "idle" });
                }
              }}
              disabled={isLoading}
              maxLength={14}
              className={cn(
                "w-full rounded-md border bg-[var(--ca-bg-soft)] py-2.5 pr-3 pl-9 font-mono text-[14px] text-[var(--ca-text-strong)] outline-none transition",
                "border-[var(--ca-line)] focus:border-[#1E40AF] focus:ring-1 focus:ring-[#1E40AF]/40",
                "disabled:cursor-wait disabled:opacity-60",
              )}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className={cn(
              "rounded-md bg-[#1E40AF] px-5 py-2.5 text-[13.5px] font-semibold text-white transition hover:bg-[#1A3899]",
              "disabled:cursor-wait disabled:opacity-70",
            )}
          >
            {isLoading ? "Ищем…" : "Найти"}
          </button>
        </div>
        {state.kind === "error" && (
          <p className="mt-2 text-[12px] text-[#B91C1C]" role="alert">
            {state.message}
          </p>
        )}
        <p className="mt-3 text-[11.5px] text-[var(--ca-text-muted)]">
          Все поисковые запросы фиксируются в журнале аудита с маскированным ИНН.
        </p>
      </form>

      {state.kind === "result" && (
        <SearchResult result={state.data} inn={state.inn} />
      )}
    </div>
  );
}
