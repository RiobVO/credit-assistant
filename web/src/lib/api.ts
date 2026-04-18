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
  score: number;
  recommendation: Recommendation;
  severity_breakdown: Partial<Record<Severity, number>>;
};

export type DossierResponseDto = {
  borrower_inn_masked: string;
  as_of: string;
  red_flags: RedFlagDto[];
  risk_score: RiskScoreDto;
  rules_evaluated: number;
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
