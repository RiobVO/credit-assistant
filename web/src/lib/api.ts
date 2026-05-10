// API-клиент для FastAPI-бэкенда. Типы зеркалят
// src/interfaces/api/shared/dossier_schema.py:DossierResponse.

import { API_URL } from "./config";

export type Severity = "low" | "medium" | "high" | "critical";
export type Recommendation = "approve" | "review" | "reject";

export type RedFlagDto = {
  rule_id: string;
  rule_version: string;
  severity: Severity;
  source: string;
  message: string;
  evidence: Record<string, unknown>;
  detected_at: string;
};

export type RiskScoreDto = {
  score: number; // raw domain (lower=better)
  display_score: number; // 100 − score (banking-style higher=better)
  recommendation: Recommendation;
  severity_breakdown: Partial<Record<Severity, number>>;
};

export type DossierResponseDto = {
  dossier_id: string;
  borrower_inn_masked: string;
  as_of: string;
  red_flags: RedFlagDto[];
  risk_score: RiskScoreDto;
  rules_evaluated: number;
};

// Зеркалит ``DossierViewResponse`` из backend (interfaces/api/shared/dossier_schema.py).
// Все Decimal-поля приходят строкой — защита от потери точности на больших
// UZS-суммах. Frontend парсит через parseFloat в местах отображения.
export type DossierViewDto = DossierResponseDto & {
  borrower: {
    inn: string;
    name: string;
    legal_form: "llc" | "pe" | "ltd" | "jsc" | "ie" | "other";
    registration_date: string; // ISO YYYY-MM-DD
    director_name: string;
    director_appointed_at: string;
    okved_main: string;
    registered_address: string;
    okved_main_changed_at: string | null;
    charter_capital: { amount: string; currency: "UZS" | "USD" } | null;
  };
  application: {
    id: string; // BR-YYYY-XXXX
    status: "in_review" | "approved" | "rejected" | "draft";
  };
  kpis: {
    revenue_ltm: KpiValueDto | null;
    ebitda: KpiValueDto | null;
    roe: KpiValueDto | null;
    debt_to_ebitda: KpiValueDto | null;
  };
  monthly_revenue_24m: Array<{
    month: string; // YYYY-MM
    revenue: string; // Decimal как str
    trend: string; // Decimal как str
    is_peak: boolean;
  }>;
};

export type KpiValueDto = {
  value: string; // Decimal как str
  unit: "UZS" | "PCT" | "RATIO";
  yoy_pct: string | null; // Decimal как str; null если сравнивать не с чем
  sparkline: string[]; // точки oldest→newest, может быть пустой
};

export type ApiErrorBody = {
  detail?: unknown;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody | string,
    message?: string,
  ) {
    super(message ?? `API ${status}`);
    this.name = "ApiError";
  }
}

export async function postManualInput(
  payload: unknown,
): Promise<DossierResponseDto> {
  return jsonFetch<DossierResponseDto>("/api/manual-input", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDossier(dossierId: string): Promise<DossierViewDto> {
  return jsonFetch<DossierViewDto>(
    `/api/dossier/${encodeURIComponent(dossierId)}`,
    { method: "GET" },
  );
}

// --- Drafts API (см. src/interfaces/api/shared/draft.py) ---

export type DraftCreatedDto = {
  draft_id: string;
  expires_at: string;
};

export type DraftResponseDto = {
  draft_id: string;
  payload: Record<string, unknown>;
};

export async function createDraft(
  payload: Record<string, unknown>,
): Promise<DraftCreatedDto> {
  return jsonFetch<DraftCreatedDto>("/api/manual-input/draft", {
    method: "POST",
    body: JSON.stringify({ payload }),
  });
}

export async function updateDraft(
  draftId: string,
  payload: Record<string, unknown>,
): Promise<DraftCreatedDto> {
  return jsonFetch<DraftCreatedDto>(
    `/api/manual-input/draft/${encodeURIComponent(draftId)}`,
    {
      method: "PUT",
      body: JSON.stringify({ payload }),
    },
  );
}

export async function getDraft(draftId: string): Promise<DraftResponseDto> {
  return jsonFetch<DraftResponseDto>(
    `/api/manual-input/draft/${encodeURIComponent(draftId)}`,
    { method: "GET" },
  );
}

// --- Soliq xltx upload (см. src/interfaces/api/shared/soliq_upload.py) ---

export type SoliqMoneyDto = { amount: string; currency: "UZS" | "USD" };
export type SoliqDateRangeDto = { start: string; end: string };

export type SoliqUploadResponseDto = {
  period: SoliqDateRangeDto;
  vat_declared: SoliqMoneyDto | null;
  esf_seller_vat_total: SoliqMoneyDto | null;
  organization_name: string;
  submitted_at: string | null;
  diff_pct: string | null;
};

export async function uploadSoliqXltx(args: {
  files: File[]; // ровно два файла: декларация + ilova (любой порядок)
  borrowerInn: string;
  periodMonth: number;
}): Promise<SoliqUploadResponseDto> {
  const fd = new FormData();
  for (const f of args.files) fd.append("files", f, f.name);
  fd.append("borrower_inn", args.borrowerInn);
  fd.append("period_month", String(args.periodMonth));

  const r = await fetch(`${API_URL}/api/upload/soliq-xltx`, {
    method: "POST",
    body: fd,
  });

  if (!r.ok) {
    let body: ApiErrorBody | string;
    try {
      body = (await r.json()) as ApiErrorBody;
    } catch {
      body = await r.text();
    }
    throw new ApiError(r.status, body);
  }
  return (await r.json()) as SoliqUploadResponseDto;
}

async function jsonFetch<T>(path: string, init: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });

  if (!r.ok) {
    let body: ApiErrorBody | string;
    try {
      body = (await r.json()) as ApiErrorBody;
    } catch {
      body = await r.text();
    }
    throw new ApiError(r.status, body);
  }

  return (await r.json()) as T;
}
