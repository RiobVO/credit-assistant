"""Snapshot mapper: round-trip + JSON-сериализуемость payload."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.gnk_certificate import GnkCertificate
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money
from infrastructure.persistence.mappers.snapshot_mapper import (
    snapshot_from_payload,
    snapshot_to_payload,
)

UZS = Currency.UZS


def _money(amount: str | int) -> Money:
    return Money(Decimal(amount), UZS)


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name='ООО "Тест"',
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов",
        director_appointed_at=date(2022, 1, 1),
        okved_main="62.01",
        registered_address="Ташкент",
    )


def _full_snapshot() -> BorrowerSnapshot:
    """Snapshot со всеми полями заполненными."""
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=[
            FinancialReport(
                period=DateRange(start=date(2024, 1, 1), end=date(2024, 12, 31)),
                revenue=_money(5_000_000_000),
                net_profit=_money(500_000_000),
                taxes_paid=_money(120_000_000),
                vat_declared=_money(300_000_000),
                balance_end=BalanceSnapshot(
                    assets=_money(4_000_000_000),
                    liabilities=_money(2_000_000_000),
                ),
            ),
        ],
        quarterly_reports=[
            FinancialReport(
                period=DateRange(start=date(2025, 1, 1), end=date(2025, 3, 31)),
                revenue=_money(1_200_000_000),
                net_profit=_money(80_000_000),
                taxes_paid=_money(20_000_000),
            ),
        ],
        monthly_turnover=[
            MonthlyTurnover(
                month_start=date(2026, 3, 1),
                revenue=_money(400_000_000),
                vat_obligations=_money(48_000_000),
            ),
            MonthlyTurnover(month_start=date(2026, 4, 1), revenue=_money(380_000_000)),
        ],
        counterparties_buyers=[
            Counterparty(
                inn=INN("200000020"),
                name="Покупатель",
                registration_date=date(2024, 1, 1),
            ),
        ],
        counterparties_suppliers=[
            Counterparty(
                inn=INN("300000030"),
                name="Поставщик",
                registration_date=date(2019, 1, 1),
            ),
        ],
        buyer_revenue_share={"200000020": Decimal("0.5")},
        supplier_purchase_share={"300000030": Decimal("0.7")},
        invoices=[
            Invoice(
                date=date(2025, 6, 1),
                amount=_money(500_000_000),
                our_role=InvoiceRole.SELLER,
                counterparty_inn=INN("200000020"),
                counterparty_name="Покупатель",
            ),
        ],
        tax_events=[
            TaxEvent(date=date(2026, 3, 1), type=TaxEventType.PAYMENT, delay_days=45),
            TaxEvent(
                date=date(2026, 2, 1),
                type=TaxEventType.PENALTY,
                amount=_money(50_000_000),
            ),
            TaxEvent(
                date=date(2025, 11, 1),
                type=TaxEventType.ACCOUNT_FREEZE,
                duration_days=30,
            ),
        ],
        vat_periods=[
            VatPeriodReport(
                period=DateRange(start=date(2026, 3, 1), end=date(2026, 3, 31)),
                vat_declared=_money(300_000_000),
                esf_seller_vat_total=_money(60_000_000),
                submitted_at=date(2026, 4, 25),
            ),
        ],
        loan_request=LoanRequest(
            amount=_money(1_500_000_000),
            term_months=24,
            rate_pct=Decimal("22.5"),
            purpose="working_capital",
            category="standard",
        ),
    )


def test_snapshot_round_trip_full() -> None:
    original = _full_snapshot()
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored == original


def test_snapshot_round_trip_empty() -> None:
    # Все коллекции пустые, опциональные поля None.
    original = BorrowerSnapshot(borrower=_borrower(), as_of=date(2026, 5, 8))
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored == original


def test_snapshot_payload_is_json_serializable() -> None:
    # JSONB на стороне Postgres делает json.dumps внутри драйвера —
    # payload не должен содержать Decimal/date/INN/Money объектов.
    payload = snapshot_to_payload(_full_snapshot())
    serialized = json.dumps(payload, ensure_ascii=False)
    # Sanity: round-trip через json не теряет структуру.
    assert json.loads(serialized) == payload


def test_financial_report_round_trip_with_taxes_paid_none() -> None:
    """CA-044: taxes_paid=None должен пережить serialize→deserialize без
    превращения в Money(0). Это и есть data-integrity контракт «не заполнено»
    vs «осознанно ноль».
    """
    original = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=[
            FinancialReport(
                period=DateRange(start=date(2024, 1, 1), end=date(2024, 12, 31)),
                revenue=_money(5_000_000_000),
                net_profit=_money(500_000_000),
                taxes_paid=None,
            ),
        ],
    )
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored.annual_reports[0].taxes_paid is None
    assert restored == original


def test_ca037_financial_report_round_trip_with_all_extensions() -> None:
    """CA-037 + ADR-0024: nullable поля (PBT/interest/equity/total_debt × end/start,
    plus D&A/OCF/current_assets/current_liabilities × end/start) переживают
    JSONB round-trip без потерь. До CA-037 KPI calculator получал None из
    snapshot_to_payload → EBIT/ROE/Debt-to-EBIT оставались пустыми. До ADR-0024
    DSCR/WC_INSUFFICIENT не имели данных.
    """
    original = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=[
            FinancialReport(
                period=DateRange(start=date(2025, 1, 1), end=date(2025, 12, 31)),
                revenue=_money(7_279_371_000),
                net_profit=_money(157_282_000),
                taxes_paid=_money(56_000_000),
                profit_before_tax=_money(189_060_000),
                interest_expense=_money(67_803_000),
                depreciation_amortization=_money(45_000_000),
                operating_cash_flow=_money(220_000_000),
                balance_end=BalanceSnapshot(
                    assets=_money(2_533_084_000),
                    liabilities=_money(985_025_000),
                    equity=_money(1_548_059_000),
                    total_debt=_money(618_267_000),
                    current_assets=_money(1_300_000_000),
                    current_liabilities=_money(700_000_000),
                    inventory=_money(180_000_000),
                ),
                balance_start=BalanceSnapshot(
                    assets=_money(2_087_582_000),
                    liabilities=_money(696_805_000),
                    equity=_money(1_390_777_000),
                    total_debt=_money(332_222_000),
                    current_assets=_money(1_050_000_000),
                    current_liabilities=_money(550_000_000),
                    inventory=_money(150_000_000),
                ),
            ),
        ],
    )
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    # Frozen dataclass equality сравнит все поля FinancialReport — если
    # хоть одно потерялось, equality упадёт.
    assert restored == original
    # Дополнительно — явная проверка на критичные для KPI поля.
    r = restored.annual_reports[0]
    assert r.profit_before_tax is not None
    assert r.profit_before_tax.amount == Decimal("189060000")
    assert r.balance_end is not None
    assert r.balance_end.equity is not None
    assert r.balance_end.equity.amount == Decimal("1548059000")
    assert r.balance_end.total_debt is not None
    assert r.balance_end.total_debt.amount == Decimal("618267000")
    # ADR-0024 поля для DSCR/WC.
    assert r.depreciation_amortization is not None
    assert r.depreciation_amortization.amount == Decimal("45000000")
    assert r.operating_cash_flow is not None
    assert r.operating_cash_flow.amount == Decimal("220000000")
    assert r.balance_end.current_assets is not None
    assert r.balance_end.current_assets.amount == Decimal("1300000000")
    assert r.balance_end.current_liabilities is not None
    assert r.balance_end.current_liabilities.amount == Decimal("700000000")
    # ADR-0024 Session 2: inventory для Quick Ratio.
    assert r.balance_end.inventory is not None
    assert r.balance_end.inventory.amount == Decimal("180000000")
    assert r.balance_start is not None
    assert r.balance_start.inventory is not None
    assert r.balance_start.inventory.amount == Decimal("150000000")


def test_ca037_legacy_payload_without_new_keys_still_loads() -> None:
    """Записи, созданные ДО CA-037, не имеют новых ключей в JSONB. Чтение
    должно вернуть None по всем 8 расширениям — обратная совместимость БД.
    """
    legacy_payload: dict[str, object] = {
        "as_of": "2025-12-31",
        "annual_reports": [
            {
                "period": {"start": "2025-01-01", "end": "2025-12-31"},
                "revenue": {"amount": "5000000000", "currency": "UZS"},
                "net_profit": {"amount": "300000000", "currency": "UZS"},
                # Никаких CA-037 ключей — записано до миграции.
            },
        ],
        "quarterly_reports": [],
        "monthly_turnover": [],
        "counterparties_buyers": [],
        "counterparties_suppliers": [],
        "buyer_revenue_share": {},
        "supplier_purchase_share": {},
        "invoices": [],
        "tax_events": [],
        "vat_periods": [],
        "loan_request": None,
    }
    restored = snapshot_from_payload(legacy_payload, _borrower())
    r = restored.annual_reports[0]
    assert r.profit_before_tax is None
    assert r.interest_expense is None
    # ADR-0024 поля тоже None для legacy.
    assert r.depreciation_amortization is None
    assert r.operating_cash_flow is None
    # CA-047 / ADR-0024: пустой BalanceSnapshot (все поля None) сворачивается
    # в None, читатели должны различать «нет snapshot» и «есть snapshot со
    # всеми None».
    assert r.balance_end is None
    assert r.balance_start is None


def test_session2_inventory_backward_compat_with_current_assets_present() -> None:
    """ADR-0024 Session 2: payload, записанный после Session 1 (есть
    current_assets/current_liabilities), но до Session 2 (нет inventory) —
    balance_end не сворачивается в None; inventory == None.
    """
    session1_payload: dict[str, object] = {
        "as_of": "2025-12-31",
        "annual_reports": [
            {
                "period": {"start": "2025-01-01", "end": "2025-12-31"},
                "revenue": {"amount": "5000000000", "currency": "UZS"},
                "net_profit": {"amount": "300000000", "currency": "UZS"},
                "current_assets": {"amount": "1300000000", "currency": "UZS"},
                "current_liabilities": {"amount": "700000000", "currency": "UZS"},
                # Никаких Session 2 ключей (inventory) — записано до Session 2.
            },
        ],
        "quarterly_reports": [],
        "monthly_turnover": [],
        "counterparties_buyers": [],
        "counterparties_suppliers": [],
        "buyer_revenue_share": {},
        "supplier_purchase_share": {},
        "invoices": [],
        "tax_events": [],
        "vat_periods": [],
        "loan_request": None,
    }
    restored = snapshot_from_payload(session1_payload, _borrower())
    r = restored.annual_reports[0]
    assert r.balance_end is not None  # current_assets есть → snapshot не пустой
    assert r.balance_end.current_assets is not None
    assert r.balance_end.current_assets.amount == Decimal("1300000000")
    assert r.balance_end.inventory is None  # Session 2 поля legacy → None


def test_snapshot_decimal_precision_preserved() -> None:
    original = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        buyer_revenue_share={
            "200000020": Decimal("0.123456789012345"),  # высокая точность
        },
    )
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored.buyer_revenue_share == original.buyer_revenue_share


def test_snapshot_gnk_certificate_round_trip() -> None:
    """T0.3: gnk_certificate сериализуется в JSONB и восстанавливается без потерь.
    file_bytes остаётся в gnk_certificates table — снапшот хранит только metadata
    + file_id ссылку (UUID)."""
    cert = GnkCertificate(
        borrower_inn=INN("305002665"),
        full_name='"ZAMIN NOZ NEMATLARI" MCHJ',
        status="active",
        okveds=["47.11", "47.19"],
        source="uploaded",
        cert_id="GNK-2026-12345",
        uploaded_at=datetime(2026, 5, 17, 22, 30, 0),
        uploaded_by_analyst_id=UUID("11111111-2222-3333-4444-555555555555"),
        file_id=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    )
    original = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        gnk_certificate=cert,
    )
    payload = snapshot_to_payload(original)
    # JSON-сериализуем — должен пройти без TypeError.
    json.dumps(payload)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored.gnk_certificate == cert


def test_snapshot_gnk_certificate_optional_none_round_trip() -> None:
    original = BorrowerSnapshot(borrower=_borrower(), as_of=date(2026, 5, 8))
    payload = snapshot_to_payload(original)
    assert payload["gnk_certificate"] is None
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored.gnk_certificate is None


def test_snapshot_legacy_payload_without_gnk_certificate_loads() -> None:
    """Существующие JSONB-записи (до T0.3) не содержат ключ gnk_certificate —
    from_payload должен мягко вернуть None."""
    payload = snapshot_to_payload(BorrowerSnapshot(borrower=_borrower(), as_of=date(2026, 5, 8)))
    del payload["gnk_certificate"]
    restored = snapshot_from_payload(payload, _borrower())
    assert restored.gnk_certificate is None
