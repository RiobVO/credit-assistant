// Client API: типы зеркалят `interfaces/api/bank/search_schema.py`.
// Fetcher'ы используются через React Query на client side; cookies
// автоматически передаются same-origin.

import type { Recommendation } from "./api";

export type BorrowerSearchResult = {
  found: boolean;
  borrower_name: string | null;
  dossier_id: string | null;
  score: number | null;
  display_score: number | null;
  created_at: string | null;
};

export type BankDossierListItem = {
  dossier_id: string;
  borrower_inn_masked: string;
  borrower_name: string;
  score: number;
  display_score: number;
  recommendation: Recommendation;
  created_at: string;
  analyst_id: string | null;
  analyst_full_name: string | null;
};

export type BankDossierListResponse = {
  items: BankDossierListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type ListFilter = "mine" | "all";

export type ListParams = {
  filter?: ListFilter;
  q?: string;
  page?: number;
  pageSize?: number;
};

export class BankApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "BankApiError";
  }
}

async function readError(resp: Response): Promise<string> {
  try {
    const body = (await resp.json()) as { detail?: string };
    return body.detail ?? `${resp.status}`;
  } catch {
    return `${resp.status}`;
  }
}

export async function searchBorrower(inn: string): Promise<BorrowerSearchResult> {
  const r = await fetch(
    `/api/bank/borrowers/search?inn=${encodeURIComponent(inn)}`,
    { credentials: "same-origin", cache: "no-store" },
  );
  if (!r.ok) throw new BankApiError(r.status, await readError(r));
  return (await r.json()) as BorrowerSearchResult;
}

export async function listDossiers(
  params: ListParams,
): Promise<BankDossierListResponse> {
  const qs = new URLSearchParams();
  if (params.filter) qs.set("filter", params.filter);
  if (params.q && params.q.trim()) qs.set("q", params.q.trim());
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("page_size", String(params.pageSize));
  const search = qs.toString();
  const r = await fetch(`/api/bank/dossiers${search ? `?${search}` : ""}`, {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!r.ok) throw new BankApiError(r.status, await readError(r));
  return (await r.json()) as BankDossierListResponse;
}

// --- helpers для отрисовки --------------------------------------------------

export type ScoreBand = "good" | "warn" | "bad";

export function scoreBand(displayScore: number | null): ScoreBand | null {
  if (displayScore === null) return null;
  if (displayScore >= 70) return "good";
  if (displayScore >= 40) return "warn";
  return "bad";
}

export function recommendationBand(rec: Recommendation): ScoreBand {
  switch (rec) {
    case "approve":
      return "good";
    case "review":
      return "warn";
    case "reject":
      return "bad";
  }
}
