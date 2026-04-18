"""VatPeriodReport: НДС-отчёт за конкретный налоговый период.

Заменяет одиночный агрегат ``BorrowerSnapshot.esf_seller_vat_total`` на список
периодных отчётов: реальные данные my3.soliq.uz приходят помесячно, и правило
``VAT_ESF_MISMATCH`` теперь сравнивает декларацию и сумму ЭСФ-продаж в рамках
**одного и того же** периода.

Источник заполнения — пара (Расчёт НДС + ilova-приложение №4) из xltx-выгрузки;
оба файла относятся к одному налоговому периоду. Маппер
``infrastructure/adapters/soliq_xltx/snapshot_mapper.py`` собирает один
``VatPeriodReport`` на пару. См. ADR 0006.
"""

from dataclasses import dataclass
from datetime import date

from domain.value_objects.date_range import DateRange
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class VatPeriodReport:
    """НДС-отчёт за период. Оба денежных поля опциональны:

    - ``vat_declared is None`` — известен реестр ЭСФ, но декларация не загружена;
    - ``esf_seller_vat_total is None`` — известна декларация, но без ilova-реестра.

    Правило ``VAT_ESF_MISMATCH`` срабатывает только когда заполнены оба поля.
    """

    period: DateRange
    vat_declared: Money | None = None
    esf_seller_vat_total: Money | None = None
    submitted_at: date | None = None
