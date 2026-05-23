"""Demo seed: 5 заранее подготовленных borrower/dossier-сценариев для pilot trip.

Сценарии 1:1 соответствуют `docs/demo/scenarios.md`:

* BR-2026-0040 — ООО «Зумрад-Текстиль» (LLC, 301234567). Score 0 / APPROVE.
* BR-2026-0042 — ФХ «Хосилот-Агро» (Farm/OTHER, 402345678). Score 0 / APPROVE.
* BR-2026-0030 — ИП «кадр дон нон» (IE, 201308534), snapshot N. Score ~6 / APPROVE.
  → DIRECTOR_CHANGED_6M (20 days) + LOW_MARGIN_HIGH_TURNOVER.
* BR-2026-0046 — тот же ИНН 201308534, snapshot N+1mo. Score ~21 / REVIEW.
  → VAT_ESF_MISMATCH critical + DIRECTOR_CHANGED_6M (65 days) + LOW_MARGIN_HIGH_TURNOVER.
* BR-2026-0047 — тот же ИНН 201308534, snapshot N+1mo + крупный заём. Score ~50 / REVIEW.
  → VAT_ESF_MISMATCH + LOAN_TO_REVENUE_RATIO + INSUFFICIENT_DATA + DIRECTOR_CHANGED_6M.

Usage:

    # Сухой прогон — JSON для проверки spec'ов:
    uv run python -m scripts.seed_demo_borrowers

    # Боевой прогон — записать demo dossiers в БД (Docker compose):
    docker compose exec api bash -c "cd /app/src && \\
        uv run --no-sync python -m scripts.seed_demo_borrowers --commit"

Свойства:

* Деттерминированные ``case_id`` — обход ``SqlAlchemyCaseIdAllocator`` через
  явный аргумент ``case_id=`` в ``DossierRepository.save``. Это допустимо
  только для seed'а: реальные dossiers всегда идут через allocator. Sequence
  по-прежнему стартует с 1; первый production dossier получит BR-2026-0001
  независимо от того, что seed занял 0030/0040/0042/0046/0047 — allocator
  читает MAX(year) при collision, fix-up — отдельная задача T1.1b если будет
  reuse-конфликт (не блокер).
* Идемпотентность — перед каждым insert проверяется существование dossier'а
  с этим case_id; есть → skip. Re-run на seeded БД печатает «skipped».

Borrower 201308534 (ИП) переиспользуется между BR-0030/0046/0047 — это часть
narrative «один заёмщик три снимка». INN уникален → upsert по INN'у вернёт
тот же borrower_id для всех трёх dossiers.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from application.dto.parsed_data_chunk import ManualChunk
from application.use_cases.build_borrower_snapshot import build_borrower_snapshot
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.vat_period_report import VatPeriodReport
from domain.services.scoring_service import ScoringService
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money
from infrastructure.persistence.database import dispose_engine, get_session_factory
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.persistence.repositories.borrower_repository import (
    SqlAlchemyBorrowerRepository,
)
from infrastructure.persistence.repositories.borrower_snapshot_repository import (
    SqlAlchemyBorrowerSnapshotRepository,
)
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from infrastructure.rules.registry_factory import load_registry

# Versioning rules engine — то же значение, что в interfaces/api/shared/dossier.py.
RULES_VERSION = "v1"

# YAML с правилами; путь идентичен interfaces/api/shared/dependencies.py.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_RULES_YAML = _REPO_ROOT / "config" / "rules" / "v1_uz_msb.yaml"

_UZS = Currency.UZS

# Анкорный «сегодня» для всех snapshots — детерминированный demo.
# Snapshots BR-0030 / BR-0046 / BR-0047 строятся как «as_of = DEMO_AS_OF +
# offset». Меняем только если scenarios.md narrative обновится.
DEMO_AS_OF: date = date(2026, 5, 20)
DEMO_CURRENT_YEAR = DEMO_AS_OF.year  # 2026


@dataclass(frozen=True, slots=True)
class DemoBorrowerSpec:
    """Spec заёмщика для seed'а. Один Borrower → возможно несколько dossiers."""

    inn: str
    name: str
    legal_form: LegalForm
    registration_date: date
    director_name: str
    # ``director_appointed_at`` базовая; конкретные snapshots могут переопределять
    # через DemoDossierSpec.director_appointed_at_override (BR-0046/0047 имитируют
    # «сменился ещё раз» для DIRECTOR_CHANGED_6M).
    director_appointed_at: date
    oked_main: str
    registered_address: str


@dataclass(frozen=True, slots=True)
class DemoDossierSpec:
    """Spec одного снимка / dossier'а. Включает overrides для borrower-полей."""

    case_id: str
    as_of: date
    industry: str
    # Финансы: список (year, revenue, net_profit, taxes_paid). Пустой → snapshot
    # без annual reports (используется для BR-0047 / INSUFFICIENT_DATA).
    annual: tuple[tuple[int, Decimal, Decimal, Decimal], ...]
    # Месячные обороты помесячно равные quarterly_revenue / 3. Если пустой —
    # monthly_turnover не пишется (INSUFFICIENT_DATA scenario).
    quarterly_revenue: tuple[Decimal, ...]
    # VAT period: (year, month, declared, esf_total). None → snapshot без VAT.
    vat_period: tuple[int, int, Decimal, Decimal] | None
    loan_request: LoanRequest | None
    # Override: позволяет «передвинуть» директорские смены для одного и того
    # же borrower'а между разными dossier'ами. None → используем base из
    # DemoBorrowerSpec.director_appointed_at.
    director_appointed_at_override: date | None = None


# Базовый borrower для clean retail (BR-0040).
ZUMRAD = DemoBorrowerSpec(
    inn="301234567",
    name="ООО «Зумрад-Текстиль»",
    legal_form=LegalForm.LLC,
    registration_date=date(2017, 4, 12),
    director_name="Каримов Шохрух Анварович",
    director_appointed_at=date(2021, 2, 15),  # > 6 мес назад → правило не fires
    oked_main="47.51",
    registered_address="г. Ташкент, Юнусабадский р-н, ул. Мустакиллик, 41",
)

# Clean agriculture (BR-0042). ФХ → LegalForm.OTHER (нет отдельного ФХ-bucket).
KHOSILOT = DemoBorrowerSpec(
    inn="402345678",
    name="ФХ «Хосилот-Агро»",
    legal_form=LegalForm.OTHER,
    registration_date=date(2014, 9, 3),
    director_name="Юлдашев Бахром Тошпулатович",
    director_appointed_at=date(2018, 6, 1),
    oked_main="01.13",
    registered_address="Ферганская обл., Бувайдинский р-н, с. Сартепа",
)

# ИП «кадр дон нон» — narrative героя BR-0030/0046/0047. Базовая дата
# назначения 2018-01-15 (старая), override'ы в DossierSpec эмулируют ребрендинг.
KADR_DON_NON = DemoBorrowerSpec(
    inn="201308534",
    name="ИП «кадр дон нон»",
    legal_form=LegalForm.IE,
    registration_date=date(2016, 3, 20),
    director_name="Эргашев Шерзод Камилович",
    director_appointed_at=date(2018, 1, 15),  # base — старый директор
    oked_main="10.71",  # производство хлеба
    registered_address="Андижанская обл., г. Андижан, ул. Бабура, 22",
)


def _annual_zumrad() -> tuple[tuple[int, Decimal, Decimal, Decimal], ...]:
    """Чистый retail: rev ~3.2 млрд, маржа ~6%, налоги ~5%. Не fires
    LOW_MARGIN_HIGH_TURNOVER (revenue < 5 млрд)."""
    return tuple(
        (
            year,
            Decimal("3200000000"),
            Decimal("3200000000") * Decimal("0.06"),
            Decimal("3200000000") * Decimal("0.05"),
        )
        for year in (DEMO_CURRENT_YEAR - 1, DEMO_CURRENT_YEAR)
    )


def _quarterly_zumrad() -> tuple[Decimal, ...]:
    base = Decimal("3200000000") / Decimal(4)
    coefs = [Decimal(str(c)) for c in (0.9, 1.0, 1.1, 1.4, 1.0, 1.1, 1.2, 1.5)]
    return tuple(base * c for c in coefs)


def _annual_khosilot() -> tuple[tuple[int, Decimal, Decimal, Decimal], ...]:
    return tuple(
        (
            year,
            Decimal("1800000000"),
            Decimal("1800000000") * Decimal("0.10"),
            Decimal("1800000000") * Decimal("0.03"),
        )
        for year in (DEMO_CURRENT_YEAR - 1, DEMO_CURRENT_YEAR)
    )


def _quarterly_khosilot() -> tuple[Decimal, ...]:
    base = Decimal("1800000000") / Decimal(4)
    coefs = [Decimal(str(c)) for c in (0.7, 1.5, 1.3, 0.8, 0.7, 1.6, 1.3, 0.9)]
    return tuple(base * c for c in coefs)


def _annual_kadr_low_margin() -> tuple[tuple[int, Decimal, Decimal, Decimal], ...]:
    """ИП с rev 7.28 млрд и margin 2.2% → fires LOW_MARGIN_HIGH_TURNOVER
    (revenue > 5 млрд И margin < 5%). Used in BR-0030 / BR-0046.
    """
    revenue = Decimal("7280000000")
    net_profit = revenue * Decimal("0.022")
    taxes = revenue * Decimal("0.04")
    return tuple(
        (year, revenue, net_profit, taxes)
        for year in (DEMO_CURRENT_YEAR - 1, DEMO_CURRENT_YEAR)
    )


def _quarterly_kadr_low_margin() -> tuple[Decimal, ...]:
    base = Decimal("7280000000") / Decimal(4)
    coefs = [Decimal(str(c)) for c in (0.9, 1.0, 1.1, 1.0, 0.95, 1.05, 1.1, 0.9)]
    return tuple(base * c for c in coefs)


# Loan request большой, чтобы DIRECTOR_CHANGED_6M прошёл material-порог
# (>500 млн UZS). collateral_type="real_estate" поднимает LOAN_TO_REVENUE
# порог до 0.70 — на BR-0030/0046 правило не fires (rev 7.28 млрд → 1 млрд
# заём → ratio 0.137, safe). На BR-0047 fires (rev 0, ratio infinity).
LOAN_KADR_NORMAL = LoanRequest(
    amount=Money(Decimal("1000000000"), _UZS),
    term_months=24,
    rate_pct=Decimal("22.0"),
    purpose="Оборотные средства / закупка муки",
    category="working_capital",
    collateral_type="real_estate",
)

# BR-0047: крупный заём 555.5 млрд при нулевой выручке. unsecured → fires
# LOAN_TO_REVENUE_RATIO по строгому 0.40 порогу (collateral=none).
LOAN_KADR_HUGE = LoanRequest(
    amount=Money(Decimal("555500000000"), _UZS),
    term_months=60,
    rate_pct=Decimal("24.5"),
    purpose="Расширение производства",
    category="capex",
    collateral_type="none",
)


def _build_dossier_specs() -> list[tuple[DemoBorrowerSpec, DemoDossierSpec]]:
    """5 пар (borrower, dossier) для seed'а в порядке case_id."""
    return [
        # BR-2026-0030: ИП с лёгкими сигналами. as_of - director_appointed = 20d.
        (
            KADR_DON_NON,
            DemoDossierSpec(
                case_id="BR-2026-0030",
                as_of=DEMO_AS_OF,
                industry="manufacturing",
                annual=_annual_kadr_low_margin(),
                quarterly_revenue=_quarterly_kadr_low_margin(),
                vat_period=None,
                loan_request=LOAN_KADR_NORMAL,
                # 20 days before as_of → fires DIRECTOR_CHANGED_6M.
                director_appointed_at_override=DEMO_AS_OF - timedelta(days=20),
            ),
        ),
        # BR-2026-0040: clean retail.
        (
            ZUMRAD,
            DemoDossierSpec(
                case_id="BR-2026-0040",
                as_of=DEMO_AS_OF,
                industry="retail",
                annual=_annual_zumrad(),
                quarterly_revenue=_quarterly_zumrad(),
                vat_period=None,
                loan_request=None,
            ),
        ),
        # BR-2026-0042: clean agriculture (Farm/OTHER).
        (
            KHOSILOT,
            DemoDossierSpec(
                case_id="BR-2026-0042",
                as_of=DEMO_AS_OF,
                industry="agro",
                annual=_annual_khosilot(),
                quarterly_revenue=_quarterly_khosilot(),
                vat_period=None,
                loan_request=None,
            ),
        ),
        # BR-2026-0046: тот же ИНН, +1 месяц, добавился VAT_ESF_MISMATCH critical.
        # vat_declared 100 млн, esf 77 млн → diff 23%. material (>10 млн ✓).
        # director-change остаётся в окне 180 дней (65 days ≤ 180).
        (
            KADR_DON_NON,
            DemoDossierSpec(
                case_id="BR-2026-0046",
                as_of=DEMO_AS_OF + timedelta(days=45),  # ~1.5 месяца после 0030
                industry="manufacturing",
                annual=_annual_kadr_low_margin(),
                quarterly_revenue=_quarterly_kadr_low_margin(),
                vat_period=(2026, 3, Decimal("100000000"), Decimal("77000000")),
                loan_request=LOAN_KADR_NORMAL,
                # Делаем так, чтобы (as_of - director_appointed) == 65 days.
                director_appointed_at_override=(
                    (DEMO_AS_OF + timedelta(days=45)) - timedelta(days=65)
                ),
            ),
        ),
        # BR-2026-0047: тот же ИНН, тот же период, добавился крупный заём + пустые
        # финансы (INSUFFICIENT_DATA fires). VAT остаётся.
        (
            KADR_DON_NON,
            DemoDossierSpec(
                case_id="BR-2026-0047",
                as_of=DEMO_AS_OF + timedelta(days=46),
                industry="manufacturing",
                annual=(),  # пусто → нет revenue → INSUFFICIENT_DATA
                quarterly_revenue=(),
                vat_period=(2026, 3, Decimal("100000000"), Decimal("77000000")),
                loan_request=LOAN_KADR_HUGE,
                director_appointed_at_override=(
                    (DEMO_AS_OF + timedelta(days=46)) - timedelta(days=65)
                ),
            ),
        ),
    ]


def _quarter_to_months(year: int, quarter_index: int) -> list[date]:
    """3 даты первых чисел месяцев для квартала (0..3 → Q1..Q4)."""
    start_month = quarter_index * 3 + 1
    return [date(year, start_month + i, 1) for i in range(3)]


def _build_borrower(
    spec: DemoBorrowerSpec, dossier_spec: DemoDossierSpec
) -> Borrower:
    director_appointed = (
        dossier_spec.director_appointed_at_override or spec.director_appointed_at
    )
    return Borrower(
        inn=INN(spec.inn),
        name=spec.name,
        legal_form=spec.legal_form,
        registration_date=spec.registration_date,
        director_name=spec.director_name,
        director_appointed_at=director_appointed,
        oked_main=spec.oked_main,
        registered_address=spec.registered_address,
    )


def _build_chunk(spec: DemoBorrowerSpec, dossier_spec: DemoDossierSpec) -> ManualChunk:
    inn = INN(spec.inn)

    annual_reports: list[FinancialReport] = []
    monthly: list[MonthlyTurnover] = []
    vat_periods: list[VatPeriodReport] = []

    for (year, revenue, net_profit, taxes_paid) in dossier_spec.annual:
        annual_reports.append(
            FinancialReport(
                period=DateRange(date(year, 1, 1), date(year, 12, 31)),
                revenue=Money(revenue, _UZS),
                net_profit=Money(net_profit, _UZS),
                taxes_paid=Money(taxes_paid, _UZS),
            )
        )

    quarterly = dossier_spec.quarterly_revenue
    if quarterly:
        # 8 кварталов: первые 4 → prior year, следующие 4 → current year.
        # Если spec даёт <8 — берём как есть, year offset скользит вместе.
        slices = [
            (DEMO_CURRENT_YEAR - 1, quarterly[0:4]),
            (DEMO_CURRENT_YEAR, quarterly[4:8]),
        ]
        for year, q_amounts in slices:
            for q_idx, q_amount in enumerate(q_amounts):
                month_amount = q_amount / Decimal(3)
                for month_start in _quarter_to_months(year, q_idx):
                    monthly.append(
                        MonthlyTurnover(
                            month_start=month_start,
                            revenue=Money(month_amount, _UZS),
                        )
                    )

    if dossier_spec.vat_period is not None:
        year, month, declared, esf = dossier_spec.vat_period
        # Период — месяц. end = последний день месяца. Для марта 2026 = 31-е.
        next_month_first = (
            date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        )
        period_end = next_month_first - timedelta(days=1)
        vat_periods.append(
            VatPeriodReport(
                period=DateRange(date(year, month, 1), period_end),
                vat_declared=Money(declared, _UZS),
                esf_seller_vat_total=Money(esf, _UZS),
            )
        )

    return ManualChunk(
        borrower_inn=inn,
        annual_reports=annual_reports,
        monthly_turnover=monthly,
        vat_periods=vat_periods,
        loan_request=dossier_spec.loan_request,
    )


def _serialize_spec(specs: list[tuple[DemoBorrowerSpec, DemoDossierSpec]]) -> str:
    out: list[dict[str, Any]] = []
    for borrower_spec, dossier_spec in specs:
        out.append(
            {
                "case_id": dossier_spec.case_id,
                "inn": borrower_spec.inn,
                "name": borrower_spec.name,
                "legal_form": borrower_spec.legal_form.value,
                "industry": dossier_spec.industry,
                "as_of": dossier_spec.as_of.isoformat(),
                "annual_count": len(dossier_spec.annual),
                "has_vat_period": dossier_spec.vat_period is not None,
                "has_loan_request": dossier_spec.loan_request is not None,
            }
        )
    return json.dumps(out, ensure_ascii=False, indent=2)


# ──────────────────────── Commit path ────────────────────────


async def _case_id_exists(session: AsyncSession, case_id: str) -> bool:
    row = await session.execute(
        select(DossierORM.id).where(DossierORM.case_id == case_id).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def _commit_dossiers() -> list[dict[str, Any]]:
    """Пишет 5 dossiers в БД. Idempotent — skip уже существующих case_id."""
    registry = load_registry(_DEFAULT_RULES_YAML)
    scoring = ScoringService()
    specs = _build_dossier_specs()
    factory = get_session_factory()
    results: list[dict[str, Any]] = []

    async with factory() as session, session.begin():
        borrower_repo = SqlAlchemyBorrowerRepository(session)
        snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(session)
        dossier_repo = SqlAlchemyDossierRepository(session)

        for borrower_spec, dossier_spec in specs:
            if await _case_id_exists(session, dossier_spec.case_id):
                results.append(
                    {
                        "case_id": dossier_spec.case_id,
                        "status": "skipped",
                        "reason": "already_exists",
                    }
                )
                continue

            borrower = _build_borrower(borrower_spec, dossier_spec)
            chunk = _build_chunk(borrower_spec, dossier_spec)
            snapshot = build_borrower_snapshot(
                borrower=borrower,
                as_of=dossier_spec.as_of,
                chunks=[chunk],
            )
            flags = registry.run_all(snapshot)
            score = scoring.score(flags)

            borrower_id = await borrower_repo.upsert(borrower)
            snapshot_id = await snapshot_repo.save(snapshot, borrower_id)
            record = DossierRecord(
                score=score.score,
                recommendation=score.recommendation.value,
                severity_breakdown={
                    sev.value: cnt for sev, cnt in score.severity_breakdown.items()
                },
                red_flags=tuple(flags),
                rules_version=RULES_VERSION,
                rules_evaluated=len(registry.rules),
            )
            dossier_id = await dossier_repo.save(
                record,
                snapshot_id,
                dossier_spec.case_id,  # bypass allocator: explicit case_id
                source_mode="bank",
                created_by_analyst_id=None,
            )
            results.append(
                {
                    "case_id": dossier_spec.case_id,
                    "status": "created",
                    "inn": borrower.inn.value,
                    "name": borrower.name,
                    "dossier_id": str(dossier_id),
                    "score": score.score,
                    "recommendation": score.recommendation.value,
                    "red_flags_count": len(flags),
                    "red_flag_ids": [f.rule_id for f in flags],
                }
            )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed 5 demo dossiers (BR-2026-0030/0040/0042/0046/0047)."
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Записать в БД. Без флага — печатает specs в stdout (dry-run).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Alias для --commit (совместимость с install.sh).",
    )
    args = parser.parse_args(argv)

    if not (args.commit or args.yes):
        print(_serialize_spec(_build_dossier_specs()))
        return 0

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _run() -> list[dict[str, Any]]:
        try:
            return await _commit_dossiers()
        finally:
            await dispose_engine()

    results = asyncio.run(_run())
    print(json.dumps(results, ensure_ascii=False, indent=2))
    created = sum(1 for r in results if r.get("status") == "created")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    print(
        f"\nSummary: created={created}, skipped={skipped}, total={len(results)}",
        file=sys.stderr,
    )
    return 0


# Backwards-compat helpers for old tests (build_demo_borrowers / DEMO_BORROWERS).
# Tests legacy — печатают 3 borrowers'а. После rewrite фокус — case_id и dossiers,
# borrower-only фабрика остаётся для downstream проверок (industry-based).


DEMO_BORROWERS: list[dict[str, Any]] = [
    {
        "case_id": d.case_id,
        "inn": b.inn,
        "name": b.name,
        "industry": d.industry,
        "legal_form": b.legal_form.name,
        "oked_main": b.oked_main,
    }
    for b, d in _build_dossier_specs()
]


def build_demo_borrowers() -> list[dict[str, Any]]:
    """Legacy view: 5 demo dossier specs (вместо прежних 3 borrowers'ов)."""
    return list(DEMO_BORROWERS)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
