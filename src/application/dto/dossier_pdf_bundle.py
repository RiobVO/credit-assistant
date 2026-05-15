"""DossierPdfBundle: данные для рендера PDF-досье.

PDF-отчёту нужно больше, чем экрану: в дополнение к KPI и monthly_revenue_24m
показываем разделы D (топ-10 контрагентов) и E (налоговая дисциплина), которых
на frontend пока нет. Считаем их в ``application.services.pdf_data_aggregator``
из того же ``BorrowerSnapshot``, что уже лежит в ``DossierViewBundle``.

Bundle композирует ``DossierViewBundle`` (не наследует) — оригинал отдаётся
без изменений на GET /api/dossier/{id}, PDF-расширение живёт отдельной структурой.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from application.dto.brand_config import BrandConfig
from application.services.observations_builder import Observations
from application.use_cases.load_dossier_for_view import DossierViewBundle
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class CounterpartyShare:
    """Запись для топ-N покупателей/поставщиков. Доля — проценты 0..100."""

    inn: str
    name: str
    share_pct: Decimal
    months_since_registration: int | None  # None если дата регистрации неизвестна
    is_new: bool  # True, если контрагент моложе 6 мес — раздел D-маркер


@dataclass(frozen=True, slots=True)
class TaxDelayEntry:
    """Один эпизод просрочки налогового платежа."""

    paid_on: date
    delay_days: int
    amount: Money | None


@dataclass(frozen=True, slots=True)
class TaxSummary:
    """Раздел E: агрегаты по налоговой дисциплине за окно snapshot.as_of − 3y."""

    delays: tuple[TaxDelayEntry, ...]
    max_delay_days: int  # 0 если нет просрочек — для правила TAX_PAYMENT_DELAYS
    penalties_total: Money | None
    account_freezes_count_12m: int
    has_freezes_12m: bool


@dataclass(frozen=True, slots=True)
class DossierPdfBundle:
    view_bundle: DossierViewBundle
    top_buyers: tuple[CounterpartyShare, ...]
    top_suppliers: tuple[CounterpartyShare, ...]
    tax_summary: TaxSummary
    # Phase 10 — tenant-aware brand + executive summary rationale на cover.
    # ``brand`` пробрасывается до renderer'а одним объектом; не размазываем
    # по куче параметров. ``observations`` — derived из snapshot+kpis+flags
    # через ``observations_builder.build_observations``.
    brand: BrandConfig
    observations: Observations
    # rule_id → human-readable name из YAML (Phase 10). Шаблон рендерит
    # F-секцию по имени правила, не по техническому rule_id (как было в v1).
    rule_names: dict[str, str]
