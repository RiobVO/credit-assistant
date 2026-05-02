"""
Demo seed: 3 realistic UZ MSB borrowers с сезонностью.

Usage:
    uv run python -m scripts.seed_demo_borrowers

Печатает JSON 3 borrower-record'ов на stdout — для inspection / последующего
manual ingest (через UI manual-input). Запись в БД пока не реализована (см.
TODO[CA-065]).

Industries:
- retail   — потребительская розница, Q4 пик (новогодние закупки).
- agro     — сельхозпроизводитель, Q2-Q3 пик (сезон уборки/переработки).
- services — B2B-услуги, ровный профиль с лёгким YoY-ростом.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from typing import Any

DEMO_BORROWERS: list[dict[str, Any]] = [
    {
        "inn": "301234567",
        "name": "ООО «Зумрад-Текстиль»",
        "industry": "retail",
        "legal_form": "LLC",
        "registration_date": "2017-04-12",
        "okved_main": "47.51",
        "director_name": "Каримов Шохрух Анварович",
        "director_appointed_at": "2021-02-15",
        "registered_address": "г. Ташкент, Юнусабадский р-н, ул. Мустакиллик, 41",
        "annual_revenue_base": Decimal("3200000000"),
        "seasonality": [0.9, 1.0, 1.1, 1.4, 1.0, 1.1, 1.2, 1.5],
    },
    {
        "inn": "402345678",
        "name": "ФХ «Хосилот-Агро»",
        "industry": "agro",
        "legal_form": "FARM",
        "registration_date": "2014-09-03",
        "okved_main": "01.13",
        "director_name": "Юлдашев Бахром Тошпулатович",
        "director_appointed_at": "2018-06-01",
        "registered_address": "Ферганская обл., Бувайдинский р-н, с. Сартепа",
        "annual_revenue_base": Decimal("1800000000"),
        "seasonality": [0.7, 1.5, 1.3, 0.8, 0.7, 1.6, 1.3, 0.9],
    },
    {
        "inn": "503456789",
        "name": "ООО «ТехноСервис Плюс»",
        "industry": "services",
        "legal_form": "LLC",
        "registration_date": "2019-11-20",
        "okved_main": "62.02",
        "director_name": "Рахимов Жасур Алишерович",
        "director_appointed_at": "2023-08-10",
        "registered_address": "г. Самарканд, ул. Регистан, 12",
        "annual_revenue_base": Decimal("950000000"),
        "seasonality": [0.90, 1.04, 0.95, 1.05, 0.95, 1.10, 1.00, 1.15],
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Записать borrowers в БД (TODO[CA-065] — пока не реализовано)",
    )
    args = parser.parse_args()
    borrowers = build_demo_borrowers()
    if args.commit:
        raise NotImplementedError(
            "--commit не реализован (TODO[CA-065]); пользуйся stdout для inspection",
        )
    print(_serialize(borrowers))


if __name__ == "__main__":
    main()
