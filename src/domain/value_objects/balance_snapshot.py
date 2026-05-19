"""BalanceSnapshot: моментальный снимок баланса (FORM_1) на одну дату.

Group полей `assets / liabilities / equity / total_debt`, который в FORM_1
приходит парой колонок (period_start, period_end). До CA-047 эти поля
жили flat в `FinancialReport` (8 nullable полей), что плодило boilerplate:
KPI calculator писал `latest.equity_period_start`, mapper-ы делали то же
самое 8 раз через round-trip. Sub-entity группирует их семантически и
позволяет читателю работать как `latest.balance_end.equity`.

ADR-0024 (2026-05-19) добавил два current-баланса (`current_assets` /
`current_liabilities`) — компоненты Working Capital и Current Ratio
для правила WC_INSUFFICIENT. Источник: IFC SME Knowledge Guide.
В UZ FORM_1 это «Краткосрочные активы / обязательства» (строки
итого по разделу II актива и разделу IV пассива). Парсер FORM_1
пока не извлекает их — поля заполняются вручную через manual-input.

Все поля nullable — FORM_1 может отдать частичный снимок (например, только
assets+liabilities без equity), мы парсим best-effort.

Currency: внутри одного snapshot все Money обязаны быть в одной валюте.
Чек откладываем — это инвариант ввода, парсер FORM_1 уже валидирует.
"""

from dataclasses import dataclass

from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class BalanceSnapshot:
    assets: Money | None = None
    liabilities: Money | None = None
    equity: Money | None = None
    total_debt: Money | None = None
    # ADR-0024: current-баланс для WC_INSUFFICIENT.
    current_assets: Money | None = None
    current_liabilities: Money | None = None

    def is_empty(self) -> bool:
        """True если все поля None — снимок не несёт информации."""
        return (
            self.assets is None
            and self.liabilities is None
            and self.equity is None
            and self.total_debt is None
            and self.current_assets is None
            and self.current_liabilities is None
        )
