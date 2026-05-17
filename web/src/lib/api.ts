// API-клиент для shared endpoints. Все запросы идут same-origin через
// Next BFF catch-all (`app/api/[...path]/route.ts`) — на bank install это
// подкладывает Authorization Bearer из httpOnly cookie, на accountant
// проходит как есть. Browser fetch к same-origin URLs автоматически
// прикладывает cookies → BFF их читает на server-side. Прямой ход на
// `${API_URL}/...` (другой origin) cookie бы не послал, а CORS-credentials
// + sameSite=lax не дружат — поэтому BFF путь обязателен.
//
// Типы зеркалят src/interfaces/api/shared/dossier_schema.py.

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
    // CA-059: заглушка под documents endpoint. null = endpoint ещё не подключён —
    // UI скрывает кнопку «Документы».
    documents_count: number | null;
  };
  kpis: {
    revenue_ltm: KpiValueDto | null;
    // CA-037: EBIT (прокси EBITDA до подключения D&A через FORM_5 / PROFIT_TAX).
    ebit: KpiValueDto | null;
    roe: KpiValueDto | null;
    debt_to_ebit: KpiValueDto | null;
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
  // CA-048: категория absolute-level порога. Заполняется только для ROE и
  // Debt-to-EBIT — frontend рисует left severity stripe на KpiCard.
  // Для прочих KPI — null (нет универсального threshold).
  level_tone?: "good" | "warn" | "bad" | null;
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
  organization_name: string | null;
  submitted_at: string | null;
  diff_pct: string | null;
  parse_warnings: string[];
  skipped_rows_count: number;
};

// CA-027 multi-file autofill. Зеркалит ``ParsedFinancialsResponse`` из
// backend (interfaces/api/shared/manual_input_parse.py). Числовые поля —
// строкой Decimal (без потери точности).
export type ParsedFinancialsDto = {
  revenue_by_year: Record<string, string>; // year (str) → Decimal as string
  net_profit_by_year: Record<string, string>;
  vat_declared_by_year: Record<string, string>;
  taxes_paid_by_year: Record<string, string>;
  // CA-037: income-statement расширения — компоненты EBIT (прокси EBITDA)
  // из FORM_2 column F/D. Подключены к payload через _form-mapper на CA-037.6.
  profit_before_tax_by_year: Record<string, string>;
  interest_expense_by_year: Record<string, string>;
  // CA-041: column E xltx, «На конец отчётного периода» — текущий срез.
  assets_total: string | null;
  liabilities_total: string | null;
  // column D xltx, «На начало отчётного периода» — для ROE avg = (start+end)/2.
  assets_total_period_start: string | null;
  liabilities_total_period_start: string | null;
  // CA-037: equity + total_debt снимки (period_end + period_start) для
  // расчётов ROE и Debt-to-EBIT. Подключаются в payload на CA-037.6.
  equity_period_end: string | null;
  equity_period_start: string | null;
  total_debt_period_end: string | null;
  total_debt_period_start: string | null;
  // field_key (например "revenue_2025", "form1.assets_total") → human label
  // «FORM_2 Q4 2025 (file.xltx)»
  source_trail: Record<string, string>;
  parse_warnings: string[];
};

export async function parseManualInputFiles(files: File[]): Promise<ParsedFinancialsDto> {
  const fd = new FormData();
  for (const f of files) fd.append("files", f, f.name);

  const r = await fetch(`/api/manual-input/parse-files`, {
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
  return (await r.json()) as ParsedFinancialsDto;
}

// CA-035 Data Readiness Assessment. Stateless POST: фронт шлёт аналитический
// срез form state Шага 2 + source_trail, бэк возвращает 4-уровневый report
// + missing_capabilities + confidence_score.
export type DataReadinessRequest = {
  annual_report_years: number[];
  full_quarter_years: number[];
  partial_quarter_years: number[];
  source_trail: Record<string, string>;
};

export type DataReadinessLevel =
  | "insufficient"
  | "minimal"
  | "standard"
  | "comprehensive";

export type DataReadinessResponse = {
  level: DataReadinessLevel;
  years_covered: number[];
  full_years: number[];
  missing_capabilities: string[];
  parser_sources: string[];
  confidence_score: string; // Decimal as string, "0" / "0.25" / "1"
};

export async function assessReadiness(
  body: DataReadinessRequest,
): Promise<DataReadinessResponse> {
  const r = await fetch(`/api/manual-input/readiness`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!r.ok) {
    let errBody: ApiErrorBody | string;
    try {
      errBody = (await r.json()) as ApiErrorBody;
    } catch {
      errBody = await r.text();
    }
    throw new ApiError(r.status, errBody);
  }
  return (await r.json()) as DataReadinessResponse;
}

// CA-035b: GET /api/dossier/{id}/readiness — readiness для готового досье
// (зеркало POST /readiness, но source_trail восстанавливается на бэке через
// heuristic по присутствию полей snapshot'а).
export async function getDossierReadiness(
  dossierId: string,
): Promise<DataReadinessResponse> {
  return jsonFetch<DataReadinessResponse>(
    `/api/dossier/${encodeURIComponent(dossierId)}/readiness`,
    { method: "GET" },
  );
}

// CA-DS17: OKVED catalog МСБ-сегмента из backend.
// Источник — config/okved/uz_msb.json через GET /api/system/okved.
// Зеркалит ``OkvedCatalogResponse`` из system_schema.py.
export type OkvedItemDto = {
  code: string;
  short_ru: string;
  full_ru: string;
  short_uz: string;
  full_uz: string;
};

export type OkvedCatalogDto = {
  items: OkvedItemDto[];
};

export async function getOkvedCatalog(): Promise<OkvedCatalogDto> {
  return jsonFetch<OkvedCatalogDto>("/api/system/okved", { method: "GET" });
}

// CA-DS24: USD/UZS rate для loan-wizard конвертации.
// Источник — config/exchange/rates.json + env override USD_UZS_RATE.
// CBU API integration → CA-DS24b. Зеркалит ``UsdRateResponse``.
export type UsdRateDto = {
  rate: string; // Decimal через JSON — парсится через parseFloat в UI
  asof: string; // ISO YYYY-MM-DD
  source: "manual" | "env" | "cbu";
};

export async function getUsdRate(): Promise<UsdRateDto> {
  return jsonFetch<UsdRateDto>("/api/system/usd-rate", { method: "GET" });
}

// T0.3: ГНК-справка (manual upload Phase A, CA-003). Бэкенд: shared/gnk_certificate.py.
// Multipart upload — bypass jsonFetch (он ставит application/json content-type).
export type GnkStatus = "active" | "suspended" | "revoked" | "unknown";
export type GnkSource = "uploaded" | "gnk_live" | "gnk_cached" | "fallback";

export type GnkCertificateDto = {
  file_id: string | null;
  borrower_inn: string;
  full_name: string;
  status: GnkStatus;
  okveds: string[];
  source: GnkSource;
  cert_id: string | null;
  uploaded_at: string | null;
  uploaded_by_analyst_id: string | null;
};

export type GnkUploadInput = {
  inn: string;
  file: File;
  fullName: string;
  status: GnkStatus;
  okveds: string[];
  certId?: string | null;
};

export async function uploadGnkCertificate(
  input: GnkUploadInput,
): Promise<GnkCertificateDto> {
  const fd = new FormData();
  fd.append("file", input.file, input.file.name);
  fd.append("full_name", input.fullName);
  fd.append("cert_status", input.status);
  fd.append("okveds", input.okveds.join(","));
  if (input.certId) fd.append("cert_id", input.certId);
  const r = await fetch(
    `/api/borrowers/${encodeURIComponent(input.inn)}/gnk-certificate`,
    { method: "POST", body: fd },
  );
  if (!r.ok) {
    let body: ApiErrorBody | string;
    try {
      body = (await r.json()) as ApiErrorBody;
    } catch {
      body = await r.text();
    }
    throw new ApiError(r.status, body);
  }
  return (await r.json()) as GnkCertificateDto;
}

export async function getGnkCertificate(
  inn: string,
): Promise<GnkCertificateDto | null> {
  const r = await fetch(
    `/api/borrowers/${encodeURIComponent(inn)}/gnk-certificate`,
  );
  if (r.status === 404) return null;
  if (!r.ok) {
    let body: ApiErrorBody | string;
    try {
      body = (await r.json()) as ApiErrorBody;
    } catch {
      body = await r.text();
    }
    throw new ApiError(r.status, body);
  }
  return (await r.json()) as GnkCertificateDto;
}

export async function uploadSoliqXltx(args: {
  files: File[]; // ровно два файла: декларация + ilova (любой порядок)
  borrowerInn: string;
  periodMonth: number;
}): Promise<SoliqUploadResponseDto> {
  const fd = new FormData();
  for (const f of args.files) fd.append("files", f, f.name);
  fd.append("borrower_inn", args.borrowerInn);
  fd.append("period_month", String(args.periodMonth));

  const r = await fetch(`/api/upload/soliq-xltx`, {
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
  const r = await fetch(path, {
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
