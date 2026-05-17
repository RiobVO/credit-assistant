"""Pydantic-схемы запроса/ответа эндпоинта ручного ввода досье.

Зеркалят сущности domain, но живут в interfaces/, чтобы domain не зависел от
HTTP/Pydantic. Маппинг pydantic → domain — в ``dossier_mapper.py``.

Все денежные поля принимаются как ``Decimal`` строкой; ``float`` запрещён в
Money по дизайну (domain.value_objects.money). Pydantic v2 валидирует Decimal
из str/int/Decimal.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.value_objects.inn import VALID_LENGTHS

CurrencyCode = Literal["UZS", "USD"]
LegalFormCode = Literal["llc", "pe", "ltd", "jsc", "ie", "other"]
TaxEventTypeCode = Literal["payment", "penalty", "account_freeze", "account_unfreeze"]
InvoiceRoleCode = Literal["seller", "buyer"]
SeverityCode = Literal["low", "medium", "high", "critical"]
RecommendationCode = Literal["approve", "review", "reject"]
ApplicationStatusCode = Literal["in_review", "approved", "rejected", "draft"]
KpiUnitCode = Literal["UZS", "PCT", "RATIO"]
KpiLevelToneCode = Literal["good", "warn", "bad"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MoneyInput(_StrictModel):
    amount: Decimal
    currency: CurrencyCode = "UZS"


class MoneyOutput(_StrictModel):
    amount: str  # Decimal сериализуем как строку — JSON float теряет точность
    currency: CurrencyCode


class DateRangeInput(_StrictModel):
    start: date
    end: date


def _validate_inn(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) not in VALID_LENGTHS:
        raise ValueError(f"INN length must be 9 or 14, got {len(cleaned)}")
    if not cleaned.isdigit():
        raise ValueError("INN must contain only digits")
    return cleaned


class BorrowerInput(_StrictModel):
    inn: str
    name: str
    legal_form: LegalFormCode
    registration_date: date
    director_name: str
    director_appointed_at: date
    okved_main: str
    registered_address: str
    okved_main_changed_at: date | None = None
    charter_capital: MoneyInput | None = None

    @field_validator("inn")
    @classmethod
    def _check_inn(cls, v: str) -> str:
        return _validate_inn(v)


class FinancialReportInput(_StrictModel):
    period: DateRangeInput
    revenue: MoneyInput
    net_profit: MoneyInput
    # CA-044: optional — пустое поле формы означает «не заполнено» (None),
    # а не «уплачено 0 сум» (это разный смысл для банковского документа).
    taxes_paid: MoneyInput | None = None
    vat_declared: MoneyInput | None = None
    assets: MoneyInput | None = None
    liabilities: MoneyInput | None = None
    # CA-037: income-statement и balance-sheet расширения для EBIT/ROE/Debt-to-EBIT.
    # Все Optional — заполняются автоматически из FORM_2 (PBT, interest) и FORM_1
    # (equity, total_debt + period_start снимки на начало того же DateRange).
    profit_before_tax: MoneyInput | None = None
    interest_expense: MoneyInput | None = None
    equity: MoneyInput | None = None
    total_debt: MoneyInput | None = None
    assets_period_start: MoneyInput | None = None
    liabilities_period_start: MoneyInput | None = None
    equity_period_start: MoneyInput | None = None
    total_debt_period_start: MoneyInput | None = None


class MonthlyTurnoverInput(_StrictModel):
    month_start: date
    revenue: MoneyInput
    vat_obligations: MoneyInput | None = None


class VatPeriodInput(_StrictModel):
    """НДС-отчёт за один налоговый период (обычно месяц).

    Оба денежных поля опциональны: правило ``VAT_ESF_MISMATCH`` срабатывает
    только когда заполнены оба. См. ADR 0006.
    """

    period: DateRangeInput
    vat_declared: MoneyInput | None = None
    esf_seller_vat_total: MoneyInput | None = None
    submitted_at: date | None = None


class CounterpartyInput(_StrictModel):
    inn: str
    name: str
    registration_date: date

    @field_validator("inn")
    @classmethod
    def _check_inn(cls, v: str) -> str:
        return _validate_inn(v)


class TaxEventInput(_StrictModel):
    date: date
    type: TaxEventTypeCode
    amount: MoneyInput | None = None
    delay_days: int | None = None
    duration_days: int | None = None


class LoanRequestInput(_StrictModel):
    """Параметры запрашиваемого кредита (CA-005). Все поля обязательны —
    UI на Шаге 3 их собирает; адаптеры файловых источников поле не заполняют."""

    amount: MoneyInput
    term_months: int = Field(gt=0)
    rate_pct: Decimal = Field(ge=0)
    purpose: str
    category: str


class InvoiceInput(_StrictModel):
    date: date
    amount: MoneyInput
    our_role: InvoiceRoleCode
    counterparty_inn: str
    counterparty_name: str

    @field_validator("counterparty_inn")
    @classmethod
    def _check_inn(cls, v: str) -> str:
        return _validate_inn(v)


class ShareEntry(_StrictModel):
    inn: str
    share: Decimal = Field(ge=0, le=1)

    @field_validator("inn")
    @classmethod
    def _check_inn(cls, v: str) -> str:
        return _validate_inn(v)


class ManualInputRequest(_StrictModel):
    """Полный payload эндпоинта ``POST /api/manual-input``.

    Содержит борровера, дату прогона ``as_of`` и все опциональные структуры
    данных. На 2.4.1 покрытие гарантирует срабатывание 5 правил из 17:
    REVENUE_DROP_MOM_30, NEGATIVE_PROFIT_3Q, LOAN_TO_REVENUE_RATIO,
    DIRECTOR_CHANGED_6M, OKVED_CHANGED_12M. Остальные правила сработают по
    мере наполнения соответствующих секций (контрагенты, ЭСФ, налоги).
    """

    borrower: BorrowerInput
    as_of: date

    annual_reports: list[FinancialReportInput] = Field(default_factory=list)
    quarterly_reports: list[FinancialReportInput] = Field(default_factory=list)
    monthly_turnover: list[MonthlyTurnoverInput] = Field(default_factory=list)

    invoices: list[InvoiceInput] = Field(default_factory=list)
    tax_events: list[TaxEventInput] = Field(default_factory=list)

    counterparties_buyers: list[CounterpartyInput] = Field(default_factory=list)
    counterparties_suppliers: list[CounterpartyInput] = Field(default_factory=list)
    buyer_revenue_share: list[ShareEntry] = Field(default_factory=list)
    supplier_purchase_share: list[ShareEntry] = Field(default_factory=list)

    vat_periods: list[VatPeriodInput] = Field(default_factory=list)
    loan_request: LoanRequestInput | None = None


class RedFlagOutput(_StrictModel):
    rule_id: str
    rule_version: str
    severity: SeverityCode
    source: str
    # T0.4 follow-up B1: UZ-перевод source. Для old snapshot'ов без source_uz
    # persistence mapper подставляет source RU как fallback (см.
    # dossier_mapper._red_flag_from_dict), поэтому поле всегда непустое.
    source_uz: str
    message: str
    evidence: dict[str, Any]
    detected_at: date


class RiskScoreOutput(_StrictModel):
    """Risk score в двух шкалах одновременно (Phase 3.B Q1, правило A).

    ``score`` — raw domain (lower=better, REJECT≥30): источник для аудита и
    логов; не показываем напрямую.

    ``display_score`` = ``100 - score`` (clamped 0..100) — banking-style
    higher=better для gauge на UI. Согласовано с дизайном экрана досье.
    """

    score: int
    display_score: int
    recommendation: RecommendationCode
    severity_breakdown: dict[SeverityCode, int]


class DossierResponse(_StrictModel):
    dossier_id: UUID
    borrower_inn_masked: str
    as_of: date
    red_flags: list[RedFlagOutput]
    risk_score: RiskScoreOutput
    rules_evaluated: int


# ---------- DossierViewResponse (Phase 3.B GET /api/dossier/{id}) -------------


class BorrowerOutput(_StrictModel):
    inn: str
    name: str
    legal_form: LegalFormCode
    registration_date: date
    director_name: str
    director_appointed_at: date
    okved_main: str
    registered_address: str
    okved_main_changed_at: date | None = None
    charter_capital: MoneyOutput | None = None


class ApplicationOutput(_StrictModel):
    """Метаданные заявки. В Phase 3.B статус всегда ``in_review`` —
    workflow approve/reject появится с UI решения аналитика (TODO).

    CA-059: ``documents_count`` — заглушка под documents endpoint.
    Сейчас mapper не выставляет → None → фронт скрывает кнопку
    «Документы», вместо misleading hardcoded `(5)`.
    """

    id: str  # `BR-YYYY-XXXX`, derived из dossier_id + created_at; deterministic
    status: ApplicationStatusCode
    documents_count: int | None = None


class KpiValueOutput(_StrictModel):
    """Значение KPI-карточки. Decimal сериализуется как str — защита от потери
    точности на больших суммах (UZS миллиарды). Frontend парсит в Number для
    отображения в Recharts (визуальная точность до тыс. — достаточная).

    CA-048: ``level_tone`` — категория absolute-level порога (good/warn/bad)
    для UI/PDF left severity stripe. Заполняется только для ROE и
    Debt-to-EBIT (см. KpiBundle docstring); для прочих KPI — None.
    """

    value: str  # Decimal как str
    unit: KpiUnitCode
    yoy_pct: str | None  # Decimal как str; None если сравнивать не с чем
    sparkline: list[str]  # точки oldest→newest, может быть пустой
    level_tone: KpiLevelToneCode | None = None


class KpiBundleOutput(_StrictModel):
    """CA-037: ``ebit`` / ``debt_to_ebit`` (вместо EBITDA-имён) — честно отражают,
    что D&A не входит в расчёт (нужен FORM_5 cashflow). Когда появятся данные —
    добавим отдельные ``ebitda`` / ``debt_to_ebitda`` рядом."""

    revenue_ltm: KpiValueOutput | None
    ebit: KpiValueOutput | None
    roe: KpiValueOutput | None
    debt_to_ebit: KpiValueOutput | None


class MonthlyRevenuePointOutput(_StrictModel):
    """Точка чарта «Выручка 24 мес». ``month`` в формате YYYY-MM."""

    month: str
    revenue: str
    trend: str
    is_peak: bool


class GnkCertificateOutput(_StrictModel):
    """T0.3.2: ГНК-справка в досье — public представление без file_bytes."""

    file_id: UUID | None = None
    full_name: str
    status: Literal["active", "suspended", "revoked", "unknown"]
    okveds: list[str]
    source: Literal["uploaded", "gnk_live", "gnk_cached", "fallback"]
    cert_id: str | None = None
    uploaded_at: str | None = None


class DossierViewResponse(_StrictModel):
    dossier_id: UUID
    borrower_inn_masked: str
    as_of: date
    red_flags: list[RedFlagOutput]
    risk_score: RiskScoreOutput
    rules_evaluated: int
    borrower: BorrowerOutput
    application: ApplicationOutput
    kpis: KpiBundleOutput
    monthly_revenue_24m: list[MonthlyRevenuePointOutput]
    # T0.3.2: optional — None если ГНК-справка не загружена (Phase A — manual
    # upload в Step 1 wizard, см. shared/gnk_certificate.py + GnkCertificateUpload).
    gnk_certificate: GnkCertificateOutput | None = None
