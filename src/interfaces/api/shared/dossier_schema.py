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

from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.value_objects.inn import VALID_LENGTHS

CurrencyCode = Literal["UZS", "USD"]
LegalFormCode = Literal["llc", "pe", "ltd", "jsc", "ie", "other"]
TaxEventTypeCode = Literal["payment", "penalty", "account_freeze", "account_unfreeze"]
InvoiceRoleCode = Literal["seller", "buyer"]
SeverityCode = Literal["low", "medium", "high", "critical"]
RecommendationCode = Literal["approve", "review", "reject"]


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
    taxes_paid: MoneyInput
    vat_declared: MoneyInput | None = None
    assets: MoneyInput | None = None
    liabilities: MoneyInput | None = None


class MonthlyTurnoverInput(_StrictModel):
    month_start: date
    revenue: MoneyInput
    vat_obligations: MoneyInput | None = None


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

    esf_seller_vat_total: MoneyInput | None = None
    loan_request_amount: MoneyInput | None = None


class RedFlagOutput(_StrictModel):
    rule_id: str
    rule_version: str
    severity: SeverityCode
    source: str
    message: str
    evidence: dict[str, Any]
    detected_at: date


class RiskScoreOutput(_StrictModel):
    score: int
    recommendation: RecommendationCode
    severity_breakdown: dict[SeverityCode, int]


class DossierResponse(_StrictModel):
    borrower_inn_masked: str
    as_of: date
    red_flags: list[RedFlagOutput]
    risk_score: RiskScoreOutput
    rules_evaluated: int
