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
  const r = await fetch(`${API_URL}/api/manual-input`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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

  return (await r.json()) as DossierResponseDto;
}
