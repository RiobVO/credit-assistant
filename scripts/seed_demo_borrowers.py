"""
Demo seed: 3 realistic UZ MSB borrowers с сезонностью.

Usage:
    # stdout JSON (inspection)
    uv run python -m scripts.seed_demo_borrowers

    # запись в БД (Docker compose):
    docker compose exec api bash -c "cd /app/src && \\
        uv run --no-sync python -m scripts.seed_demo_borrowers --commit"

Industries:
- retail   — потребительская розница, Q4 пик (новогодние закупки).
- agro     — сельхозпроизводитель, Q2-Q3 пик (сезон уборки/переработки).
- services — B2B-услуги, ровный профиль с лёгким YoY-ростом.

--commit пишет полную цепочку Borrower → BorrowerSnapshot → Dossier через те
же use case и repos, что POST /api/manual-input. ``source_mode='bank'``,
``created_by_analyst_id=None`` — досье видны в bank /history без owner-фильтра.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from application.dto.dossier_record import DossierRecord
from application.dto.parsed_data_chunk import ManualChunk
from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator
from application.use_cases.build_borrower_snapshot import build_borrower_snapshot
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.services.scoring_service import ScoringService
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money
from infrastructure.persistence.database import dispose_engine, get_session_factory
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

# Soliq Money всегда UZS (см. PROJECT_BRIEF Section 6 + договорённость по фикстурам).
_UZS = Currency.UZS

# Анкорный «текущий год» для demo. Сегодня 2026 → latest annual = 2025, prior = 2024.
# Анкор делается константой, а не date.today(), чтобы demo был детерминированный
# (повторный запуск seed-а даёт ту же выручку, как в фикстурах для smoke).
DEMO_CURRENT_YEAR = 2025

# LegalForm маппинг для demo. «FARM» (ФХ — фермерское хозяйство) в domain enum
# не выделено отдельно; ближайший правильный bucket — OTHER. Не меняем enum
# ради seed-скрипта — domain остаётся стабильным.
_LEGAL_FORM_MAP: dict[str, LegalForm] = {
    "LLC": LegalForm.LLC,
    "FARM": LegalForm.OTHER,
    "PE": LegalForm.PE,
}

DEMO_BORROWERS: list[dict[str, Any]] = [
    {
        "inn": "301234567",
        "name": "ООО «Зумрад-Текстиль»",
        "industry": "retail",
        "legal_form": "LLC",
        "registration_date": "2017-04-12",
        "oked_main": "47.51",
        "director_name": "Каримов Шохрух Анварович",
        "director_appointed_at": "2021-02-15",
        "registered_address": "г. Ташкент, Юнусабадский р-н, ул. Мустакиллик, 41",
        "annual_revenue_base": Decimal("3200000000"),
        # 8 кварталов: индексы 0-3 → prior year (2024), 4-7 → current year (2025).
        "seasonality": [0.9, 1.0, 1.1, 1.4, 1.0, 1.1, 1.2, 1.5],
        # Маржа и налоги — доли от revenue. Retail: средняя маржа ~6%, налоги ~5%.
        "net_profit_pct": Decimal("0.06"),
        "taxes_pct": Decimal("0.05"),
    },
    {
        "inn": "402345678",
        "name": "ФХ «Хосилот-Агро»",
        "industry": "agro",
        "legal_form": "FARM",
        "registration_date": "2014-09-03",
        "oked_main": "01.13",
        "director_name": "Юлдашев Бахром Тошпулатович",
        "director_appointed_at": "2018-06-01",
        "registered_address": "Ферганская обл., Бувайдинский р-н, с. Сартепа",
        "annual_revenue_base": Decimal("1800000000"),
        "seasonality": [0.7, 1.5, 1.3, 0.8, 0.7, 1.6, 1.3, 0.9],
        # Agro: маржа ~10% (сезонная), налоги ~3% (льготы для ФХ).
        "net_profit_pct": Decimal("0.10"),
        "taxes_pct": Decimal("0.03"),
    },
    {
        "inn": "503456789",
        "name": "ООО «ТехноСервис Плюс»",
        "industry": "services",
        "legal_form": "LLC",
        "registration_date": "2019-11-20",
        "oked_main": "62.02",
        "director_name": "Рахимов Жасур Алишерович",
        "director_appointed_at": "2023-08-10",
        "registered_address": "г. Самарканд, ул. Регистан, 12",
        "annual_revenue_base": Decimal("950000000"),
        "seasonality": [0.90, 1.04, 0.95, 1.05, 0.95, 1.10, 1.00, 1.15],
        # B2B services: маржа ~14% (высокий margin), налоги ~7%.
        "net_profit_pct": Decimal("0.14"),
        "taxes_pct": Decimal("0.07"),
    },
]


def build_demo_borrowers() -> list[dict[str, Any]]:
    """Возвращает 3 borrower-record'а с quarterly_revenue (8 кварталов)."""
    result: list[dict[str, Any]] = []
    for spec in DEMO_BORROWERS:
        quarterly_base = spec["annual_revenue_base"] / Decimal(4)
        quarterly = [
            quarterly_base * Decimal(str(coef)) for coef in spec["seasonality"]
        ]
        record = {
            k: v
            for k, v in spec.items()
            if k not in ("annual_revenue_base", "seasonality")
        }
        record["quarterly_revenue"] = quarterly
        result.append(record)
    return result


def _serialize(borrowers: list[dict[str, Any]]) -> str:
    return json.dumps(
        borrowers,
        ensure_ascii=False,
        indent=2,
        default=lambda v: str(v) if isinstance(v, Decimal) else v,
    )


# ──────────────────────── Domain factory ────────────────────────


def _spec_to_borrower(spec: dict[str, Any]) -> Borrower:
    legal_form = _LEGAL_FORM_MAP.get(spec["legal_form"], LegalForm.OTHER)
    return Borrower(
        inn=INN(spec["inn"]),
        name=spec["name"],
        legal_form=legal_form,
        registration_date=date.fromisoformat(spec["registration_date"]),
        director_name=spec["director_name"],
        director_appointed_at=date.fromisoformat(spec["director_appointed_at"]),
        oked_main=spec["oked_main"],
        registered_address=spec["registered_address"],
    )


def _quarter_to_months(year: int, quarter_index: int) -> list[date]:
    """Возвращает 3 даты (1-е числа месяцев) для квартала.

    quarter_index 0..3 → Q1..Q4.
    """
    start_month = quarter_index * 3 + 1
    return [date(year, start_month + i, 1) for i in range(3)]


def _spec_to_chunk(spec: dict[str, Any]) -> ManualChunk:
    """Превращает demo-spec в ManualChunk: 2 annual + 24 monthly."""
    inn = INN(spec["inn"])
    quarterly_base = spec["annual_revenue_base"] / Decimal(4)
    quarterly_amounts = [
        quarterly_base * Decimal(str(coef)) for coef in spec["seasonality"]
    ]

    annual_reports: list[FinancialReport] = []
    monthly_turnover: list[MonthlyTurnover] = []

    # Кварталы 0-3 → prior year, 4-7 → current year.
    for year_offset, slice_start in [(-1, 0), (0, 4)]:
        year = DEMO_CURRENT_YEAR + year_offset
        year_quarters = quarterly_amounts[slice_start : slice_start + 4]
        year_revenue = sum(year_quarters, start=Decimal(0))
        net_profit_amount = year_revenue * spec["net_profit_pct"]
        taxes_amount = year_revenue * spec["taxes_pct"]

        annual_reports.append(
            FinancialReport(
                period=DateRange(date(year, 1, 1), date(year, 12, 31)),
                revenue=Money(year_revenue, _UZS),
                net_profit=Money(net_profit_amount, _UZS),
                taxes_paid=Money(taxes_amount, _UZS),
            )
        )

        # Квартал делим на 3 равных месяца — детерминированно, без шума.
        for q_idx, q_amount in enumerate(year_quarters):
            month_amount = q_amount / Decimal(3)
            for month_start in _quarter_to_months(year, q_idx):
                monthly_turnover.append(
                    MonthlyTurnover(
                        month_start=month_start,
                        revenue=Money(month_amount, _UZS),
                    )
                )

    return ManualChunk(
        borrower_inn=inn,
        annual_reports=annual_reports,
        monthly_turnover=monthly_turnover,
    )


# ──────────────────────── Commit path ────────────────────────


async def _commit_borrowers() -> list[dict[str, Any]]:
    """Пишет 3 demo borrowers в БД через стандартный E2E путь.

    Returns: список dict'ов {inn, dossier_id, score, recommendation} для stdout.
    """
    registry = load_registry(_DEFAULT_RULES_YAML)
    scoring = ScoringService()
    today = date.today()

    results: list[dict[str, Any]] = []
    factory = get_session_factory()

    # Одна транзакция на все 3 borrowers: атомарно.
    async with factory() as session, session.begin():
        borrower_repo = SqlAlchemyBorrowerRepository(session)
        snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(session)
        dossier_repo = SqlAlchemyDossierRepository(session)

        for spec in DEMO_BORROWERS:
            borrower = _spec_to_borrower(spec)
            chunk = _spec_to_chunk(spec)
            snapshot = build_borrower_snapshot(
                borrower=borrower,
                as_of=today,
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
            # T1.1: case_id выдаёт allocator под текущий год; sequence
            # + advisory lock гарантируют monotonic в одной транзакции
            # с save dossier.
            allocator = SqlAlchemyCaseIdAllocator(session)
            case_id = await allocator.allocate(datetime.now(UTC))
            dossier_id = await dossier_repo.save(
                record,
                snapshot_id,
                case_id,
                source_mode="bank",
                created_by_analyst_id=None,
            )
            results.append(
                {
                    "inn": borrower.inn.value,
                    "name": borrower.name,
                    "industry": spec["industry"],
                    "dossier_id": str(dossier_id),
                    "score": score.score,
                    "recommendation": score.recommendation.value,
                    "red_flags_count": len(flags),
                }
            )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Записать borrowers в БД (Borrower → BorrowerSnapshot → Dossier).",
    )
    args = parser.parse_args(argv)

    if not args.commit:
        borrowers = build_demo_borrowers()
        print(_serialize(borrowers))
        return 0

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _run() -> list[dict[str, Any]]:
        try:
            return await _commit_borrowers()
        finally:
            await dispose_engine()

    results = asyncio.run(_run())
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
