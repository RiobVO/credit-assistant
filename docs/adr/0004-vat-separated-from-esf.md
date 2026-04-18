# ADR 0004: VAT хранится отдельно от ЭСФ

- **Status**: Accepted (partially superseded by ADR 0006)
- **Date**: 2026-05-08
- **Phase**: 2

> **Note (2.3 Day 2):** одиночное поле `BorrowerSnapshot.esf_seller_vat_total`
> заменено на список `vat_periods: list[VatPeriodReport]` — см. ADR 0006.
> Мотивация удаления `Invoice.vat_amount` (этот ADR) актуальна; конкретное место
> хранения VAT-агрегата мигрировало.

## Context

Phase 2 начинается с парсинга реальной выгрузки `factura_sent_<inn>_*.csv` из e-factura.uz. Реальные колонки CSV:

```
№; ID; СТАТУС; СЧЁТ-ФАКТУРА; ТИП ЭСФ; ДОГОВОР;
ПРОДАВЕЦ (ИНН); ПРОДАВЕЦ (НАИМЕНОВАНИЕ); ПРОДАВЕЦ (КОД ФИЛИАЛА); ПРОДАВЕЦ (НАЗВАНИЕ ФИЛИАЛА);
ПОКУПАТЕЛЬ (ИНН); ПОКУПАТЕЛЬ (НАИМЕНОВАНИЕ); ПОКУПАТЕЛЬ (КОД ФИЛИАЛА); ПОКУПАТЕЛЬ (НАЗВАНИЕ ФИЛИАЛА);
СУММА К ОПЛАТЕ; ПРИМЕЧАНИЕ
```

**Колонки `НДС` нет.** Только итоговая `СУММА К ОПЛАТЕ`. Phase 1 ввёл `Invoice.vat_amount: Money` исходя из гипотезы про XML-формат Soliq, в котором НДС присутствует. CSV-источник эту гипотезу не подтверждает.

Альтернативы:

- **(A) Сделать `Invoice.vat_amount: Money | None`.** Per-invoice опциональное поле. Минус: правило `VAT_ESF_MISMATCH` всё равно агрегирует — на уровне правила приходится разбирать дырки. Per-invoice VAT не используется ни в одном из 17 правил, ценность поля = 0.
- **(B) Вычислять VAT арифметически: `amount * 12/112`.** Минус: ложь. Часть ЭСФ выпускается без НДС (упрощёнка, экспорт, льготные категории). На реальных данных получим систематическое завышение seller VAT и ложные срабатывания `VAT_ESF_MISMATCH`.
- **(C, выбрано) Убрать VAT из `Invoice` совсем; ввести агрегат `BorrowerSnapshot.esf_seller_vat_total: Money | None`.** Заполняется отдельным VAT-адаптером (источник — XML-выгрузка ЭСФ с разбивкой НДС либо сводная справка по НДС из Soliq). Когда источник — только CSV, агрегат `None`, правило молчит (degraded).

## Decision

1. `Invoice` теряет поле `vat_amount`. Остаётся: `date`, `amount`, `our_role`, `counterparty_inn`, `counterparty_name`.
2. `BorrowerSnapshot` получает опциональное поле `esf_seller_vat_total: Money | None = None`. Семантика — суммарный НДС по ЭСФ-продажам за период последнего годового отчёта. Заполняет отдельный адаптер.
3. `VAT_ESF_MISMATCH` (правило 5) переписан:
   - читает `snapshot.esf_seller_vat_total`, не агрегирует invoices;
   - если `esf_seller_vat_total is None` → молчит (degraded mode для CSV-only источников);
   - в остальном порог 15%, источник и confidence не меняются.

## Consequences

**Плюсы:**
- Адаптер CSV (Phase 2.2) не выдумывает данные, которых нет в источнике.
- Правило `VAT_ESF_MISMATCH` явно сигнализирует degraded-режим (молчит вместо false positive).
- Структура `Invoice` соответствует тому, что реально приходит из ЭСФ-выгрузок.

**Минусы:**
- `VAT_ESF_MISMATCH` срабатывает только когда есть VAT-адаптер. Phase 2 требует написать второй адаптер (Soliq XML или сводная справка НДС) для активации правила на реальных данных.
- Ответственность за корректность агрегата уходит из правила в адаптер. Тестируется на уровне адаптера, не правила.

## Impact на код

Изменены: `src/domain/entities/invoice.py`, `src/domain/entities/borrower_snapshot.py`, `src/domain/rules/financial/vat_esf_mismatch.py`, тесты + `tests/fixtures/synthetic_borrowers.py`. 218 тестов passed, coverage `src/domain/rules` сохранён ≈ 99%.

## References

- `PROJECT_BRIEF.md` Section 5 (правило `VAT_ESF_MISMATCH`), Section 6 (Data Adapters).
- `src/domain/rules/financial/vat_esf_mismatch.py`.
- ADR 0003 — общий дизайн rules engine.
