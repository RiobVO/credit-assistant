# ADR 0006: VAT-отчётность по месячным периодам (VatPeriodReport)

- **Status**: Accepted
- **Date**: 2026-05-08
- **Phase**: 2 (подфаза 2.3 Day 2)
- **Supersedes (partially)**: ADR 0004 в части одиночного `BorrowerSnapshot.esf_seller_vat_total`

## Context

ADR 0004 ввёл одиночный агрегат `BorrowerSnapshot.esf_seller_vat_total: Money | None`
с семантикой «суммарный НДС по ЭСФ-продажам за период последнего годового отчёта».
Правило `VAT_ESF_MISMATCH` сравнивало этот агрегат с `vat_declared` в latest
`annual_reports`.

Day 1 подфазы 2.3 принёс реальные данные: папа выгрузил 5 xltx-форм из
my3.soliq.uz, среди них **месячная декларация НДС** (март 2026) и
ilova-приложение №4 (реестр ЭСФ построчно с НДС за тот же месяц). Соответствие
«годовая декларация ↔ годовой агрегат ЭСФ» в реальных данных не наблюдается —
налогоплательщики НДС в Узбекистане сдают **помесячно**, годовой агрегат —
синтетический и не привязан к фактическому налоговому периоду.

Сравнивать декларацию за март с годовым агрегатом ЭСФ за весь 2025 — это
методологическая ошибка: разные периоды, несравнимые величины.

## Decision

1. Введена новая domain-сущность `VatPeriodReport` (`src/domain/entities/`):

   ```python
   @dataclass(frozen=True, slots=True)
   class VatPeriodReport:
       period: DateRange
       vat_declared: Money | None = None
       esf_seller_vat_total: Money | None = None
       submitted_at: date | None = None
   ```

2. `BorrowerSnapshot.esf_seller_vat_total: Money | None` **удалено**. Вместо него:

   ```python
   vat_periods: list[VatPeriodReport] = field(default_factory=list)
   ```

3. Правило `VAT_ESF_MISMATCH` переписано:
   - выбирает **latest period** по `period.end`, у которого заполнены **оба**
     поля (`vat_declared` и `esf_seller_vat_total`);
   - без полного периода → молчит (degraded mode для адаптеров, давших только
     одну сторону данных);
   - threshold 15%, источник, confidence — без изменений.

4. `SoliqChunk` теряет одиночное поле `esf_seller_vat_total`, получает
   `vat_periods: list[VatPeriodReport]`. `ManualChunk` получает то же поле
   (бухгалтер может вводить VAT-периоды через ручной ввод).

5. Маппер `infrastructure/adapters/soliq_xltx/snapshot_mapper.py` собирает один
   `VatPeriodReport` из пары (Расчёт НДС, ilova-приложение №4):
   - `period` строится из `declaration.header.period_year` + явного параметра
     `period_month: int` (UI/API знает период);
   - `vat_declared` ← `declaration.vat_charged_total`;
   - `esf_seller_vat_total` ← `registry.sales_vat_total`;
   - `submitted_at` ← `declaration.header.submitted_at`.

6. Persistence: JSONB-payload в `infrastructure/persistence/mappers/snapshot_mapper.py`
   получает массив `vat_periods`; одиночное поле `esf_seller_vat_total` из
   payload удалено. Существующих production-записей нет, миграция данных не
   нужна.

7. API: `ManualInputRequest` (Pydantic) теряет поле `esf_seller_vat_total`,
   получает `vat_periods: list[VatPeriodInput]`. Текущий frontend
   (Шаг 2 manual-input UI) этого поля не отправлял — breaking change без
   практических последствий.

## Alternatives considered

- **Расширить `FinancialReport` Optional-полями для VAT**. Минус: `revenue`,
  `net_profit`, `taxes_paid` не имеют смысла в чистой VAT-форме — получили бы
  множество `None` и невнятную семантику отчёта.
- **Хранить `esf_seller_vat_total: dict[period_key, Money]`**. Асимметрично с
  doman-конвенцией списков сущностей (`annual_reports`, `monthly_turnover`).
- **Оставить старое поле рядом с `vat_periods`**. Backward-compat в обмен на
  два пути в правиле и риск рассинхрона. Отвергнуто: production-данных нет.

## Consequences

**Плюсы:**
- Правило и данные методологически согласованы — сравнение в рамках одного
  налогового периода.
- Маппер xltx закрывает `VAT_ESF_MISMATCH` на реальных данных папы:
  ilova-реестр даёт `esf_seller_vat_total` точно (Decimal до копейки),
  декларация даёт `vat_declared` напрямую. Smoke на реальных файлах: declared
  62.8M ↔ ilova 63.5M, diff 1.19% — правило молчит (фирма здоровая).
- Расширяемо: квартальные/годовые VAT-периоды представимы тем же
  `VatPeriodReport(period=DateRange(...))`.

**Минусы:**
- `period_month` передаётся явным параметром в маппер xltx — UI/API должен его
  знать. Альтернатива (парсить из workbook) хрупкая: координаты ячеек Soliq
  нестабильны, шапка декларации не содержит фиксированной cell с номером месяца.
- ADR 0004 частично устарел: одиночный агрегат больше не существует. Сам ADR
  оставлен для исторического контекста (мотивация удаления `Invoice.vat_amount`
  актуальна), но в шапке отмечено «partially superseded by ADR 0006».

## Impact на код

Изменены:
- `src/domain/entities/{borrower_snapshot,invoice}.py` (+ новый
  `vat_period_report.py` + test)
- `src/domain/rules/financial/vat_esf_mismatch.py` + test
- `src/application/dto/parsed_data_chunk.py`
- `src/application/use_cases/build_borrower_snapshot.py` + test
- `src/infrastructure/adapters/soliq_xltx/snapshot_mapper.py` (новый) + test
- `src/infrastructure/persistence/mappers/snapshot_mapper.py` + test
- `src/interfaces/api/shared/{dossier_schema,dossier_mapper}.py`
- `tests/fixtures/synthetic_borrowers.py`

## References

- ADR 0004 — мотивация удаления per-invoice VAT.
- `PROJECT_BRIEF.md` Section 5 (правило `VAT_ESF_MISMATCH`).
- `docs/CLAUDE.md` Session Log — 2.3 Day 1 (парсеры) → 2.3 Day 2 (этот ADR).
