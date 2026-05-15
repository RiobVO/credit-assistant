# T2.3 — PROFIT_TAX parser (CA-029b)

> Tier 2 / Data quality / first item. Closes 5 xfail в `tests/parsers/real_xltx_test.py`. Подключает `taxes_paid_by_year` к авто-филу из PROFIT_TAX-выгрузок.

## Goal

Реализовать парсер PROFIT_TAX (Расчёт налога на прибыль юридических лиц, 15-16 листов), подключить к `parse_manual_input_files` use case, замапить «Сумму налога на прибыль – всего» (list01 L39, код 080) в `ParsedFinancials.taxes_paid_by_year[year]`.

## Real-data baseline (5 фикстур в `tests/fixtures/soliq_xltx/`)

| Фирма | ИНН | Период | Совок.доход | Налог (L39) | Случай |
|---|---|---|---|---|---|
| QADR DON NON | 201308534 | 2025 Q4 | 7.28B | 31.78M | прибыльная |
| ZAMIN | 305002665 | 2025 Q4 | 1.12B | 0 | убыток |
| GOF-KAR | 305738460 | 2025 Q4 | 4.15B | 0 | убыток |
| METALL SEMENT | 308747266 | 2025 Q4 | 0.60B | 0 | убыток (док.тип 2) |
| ZAMIN | 305002665 | 2026 Q1 | 0.32B | 0 | quarterly (skip) |

Координаты сводки (list01, столбец L = значение, K = код):
- L29 (010) Совокупный доход всего
- L30 (020) Вычитаемые расходы
- L31 (030) Налогооблагаемая прибыль (может быть отрицательной → убыток)
- L34 (060) Налоговая база
- L36 (070) Ставка налога %, **только для Q4**: в Q1-фикстуре L36 = мусор
- L39 (080) Сумма налога на прибыль – всего (gross computed) **← `taxes_paid_by_year`**
- L46 (150) Общая сумма к уплате в бюджет (post-advance, None в Q1)

Multiplier = **×1** (полные сум, не тыс.). Cross-check: PROFIT_TAX L29 (1,116,265,183) ≈ FORM_2 F6 × 1000 (1,116,265,000) для ZAMIN.

## Approved decisions

- **A** taxes_paid source: **L39 (gross computed, код 080)**.
- **B** Quarterly (Q1/Q2/Q3) PROFIT_TAX: **silent skip с warning**, mirror FORM_2 CA-027 option b.
- **C** DTO scope: **минимум — `header` + `taxable_profit` (L31) + `profit_tax_total` (L39)**. Extend по требованию.
- **D** Cross-validate FORM_2 G30 vs PROFIT_TAX L39: **backlog**, не блокер T2.3.
- **E** CA-DS25 sparkline claim в roadmap — **корректировка docs**: T2.3 не закрывает sparkline (нужен monthly_turnover источник, не PROFIT_TAX).
- **F** xfail в `real_xltx_test.py`: **удалить ветку**.

## Files affected (~11)

**New:**
1. `src/infrastructure/adapters/soliq_xltx/profit_tax_parser.py`
2. `src/infrastructure/adapters/soliq_xltx/profit_tax_parser_test.py`

**Modified:**
3. `tests/fixtures/soliq_xltx/_factories.py` — добавить `make_profit_tax_workbook(...)` factory.
4. `src/infrastructure/adapters/soliq_xltx/parser.py` — `ParsedSoliqXltx` union + dispatch.
5. `src/infrastructure/adapters/soliq_xltx/parser_test.py` — dispatch-test.
6. `src/application/use_cases/parse_manual_input_files.py` — `_merge_profit_tax` wiring.
7. `src/application/use_cases/parse_manual_input_files_test.py` — extend (если файл есть; иначе пропускаем).
8. `src/application/dto/parsed_financials.py` — docstring fix.
9. `src/application/use_cases/load_dossier_readiness.py` — comment cleanup.
10. `tests/parsers/real_xltx_test.py` — drop xfail PROFIT_TAX branch.
11. `docs/pre-demo-roadmap.md` + `CLAUDE.md` — T2.3 DONE + CA-DS25 claim correction.

**Не трогаем:** `domain/entities/financial_report.py`, `snapshot_mapper.py`, `kpi_calculator.py`, `format_detector.py`, `header_parser.py` (все уже готовы).

## TDD atomic commits

### Commit 1 — `feat(parsers): T2.3.1 PROFIT_TAX parser + synthetic factory`

**RED:**
- Добавить `make_profit_tax_workbook(inn, year, quarter, taxable_profit, profit_tax_total, ...)` в `_factories.py` (helper для tests; копия паттерна `make_form2_workbook` — list01 sentinel B2 «РАСЧЕТ\nналога на прибыль» + header cells + L29/L30/L31/L36/L39/L46).
- `profit_tax_parser_test.py`:
  - `test_parse_profit_tax_happy_path`: factory → parse → assert header.borrower_inn / year / quarter, taxable_profit Money, profit_tax_total Money, no warnings.
  - `test_parse_profit_tax_rejects_wrong_format`: form2-factory → `parse_profit_tax(wb)` → `UnsupportedFormatError`.
  - `test_parse_profit_tax_missing_list01`: workbook без list01 → `UnsupportedFormatError`.
  - `test_parse_profit_tax_negative_taxable_profit`: убыток в L31 → парсится как Money с отрицательным amount.
  - `test_parse_profit_tax_malformed_cells_warn`: текст в L39 → warning + None, не raise.
  - `test_parse_profit_tax_x_marker_silent`: 'x' в L31 → None без warning (как form2 `_is_missing`).

**GREEN:**
- `profit_tax_parser.py`: `ProfitTaxData` dataclass (`header`, `taxable_profit: Money | None`, `profit_tax_total: Money | None`, `parse_warnings: list[str]`). `parse_profit_tax(wb)` → detect_format check, `parse_header(wb, PROFIT_TAX)`, чтение L31 и L39 через `_money_full` helper (×1, не ×1000). Best-effort cell-level → warn+None.

**Verify:**
- `pytest src/infrastructure/adapters/soliq_xltx/profit_tax_parser_test.py -v` → all green.
- `ruff check src/infrastructure/adapters/soliq_xltx/profit_tax_parser.py` clean.
- `mypy --strict src/infrastructure/adapters/soliq_xltx/profit_tax_parser.py` clean.

### Commit 2 — `feat(parsers): T2.3.2 dispatch PROFIT_TAX в SoliqXltxAdapter`

**RED:**
- `parser_test.py` extend: `test_parse_dispatches_profit_tax` — feed factory-PROFIT_TAX workbook through `SoliqXltxAdapter().parse(...)`, expect `ProfitTaxData` instance.

**GREEN:**
- `parser.py`:
  - `ParsedSoliqXltx = VatDeclarationData | VatRegistryData | Form2IncomeStatementData | Form1BalanceSheetData | ProfitTaxData`.
  - `_dispatch`: добавить branch `if fmt is SoliqXltxFormat.PROFIT_TAX: return parse_profit_tax(wb)`. Удалить «PROFIT_TAX» из текста `UnsupportedFormatError`.
  - Удалить docstring lines 9-11 («Profit Tax распознаётся ... но специализированного парсера для него ещё нет (TODO[CA-029])»).

**Verify:**
- `pytest src/infrastructure/adapters/soliq_xltx/parser_test.py -v` green.

### Commit 3 — `feat(use-case): T2.3.3 PROFIT_TAX → taxes_paid_by_year в parse_manual_input_files`

**RED:**
- `parse_manual_input_files_test.py` (если не существует — проверить, may already exist as `*_test.py` co-located):
  - `test_profit_tax_q4_populates_taxes_paid`: NamedFile с profit_tax_2025_full → `ParsedFinancials.taxes_paid_by_year[2025] == Decimal("31_777_673.85")`, source_trail `"taxes_paid_2025"` контентом `"PROFIT_TAX 2025 (filename)"`.
  - `test_profit_tax_q1_skipped_with_warning`: NamedFile с Q1 → `taxes_paid_by_year` empty, warning «промежуточный YTD, не годовой total — пропуск (полный год = Q4-файл)».
  - `test_profit_tax_same_year_first_wins`: 2 PROFIT_TAX за один год → first wins, warning.
  - `test_profit_tax_zero_loss_year`: убыточная фирма → `taxes_paid_by_year[year] == Decimal(0)` (Money(0) проходит, это не None).

**GREEN:**
- `parse_manual_input_files.py`:
  - Import `ProfitTaxData`.
  - В loop добавить `elif isinstance(parsed, ProfitTaxData): _merge_profit_tax(parsed, f.name, taxes_paid_by_year, source_trail, warnings)`.
  - Новая функция `_merge_profit_tax(parsed, filename, taxes_paid_by_year, source_trail, warnings)`:
    - `year = parsed.header.period_year` → None → warning + return.
    - `quarter = parsed.header.period_index` — не None и != 4 → warning «промежуточный YTD…» + return.
    - `parsed.profit_tax_total is None` → warning «PROFIT_TAX без суммы налога в L39» + return.
    - `_set_once(taxes_paid_by_year, year, parsed.profit_tax_total, source_trail, "taxes_paid", f"PROFIT_TAX {year} ({filename})", warnings)`.
    - Прокинуть `parsed.parse_warnings` с `{filename}:` префиксом.

**Verify:**
- `pytest src/application/use_cases/parse_manual_input_files_test.py -v` green.
- `pytest src/application/ -v` no regression.

### Commit 4 — `chore(docs): T2.3.4 cleanup TODO[CA-029] follow-ups + drop real_xltx xfail`

- `parsed_financials.py:33-35` docstring: убрать «парсер PROFIT_TAX не реализован (TODO[CA-029b])», заменить на «заполняется из PROFIT_TAX list01 L39 (код 080), gross computed — см. T2.3».
- `load_dossier_readiness.py:85-86` comment: убрать «PROFIT_TAX парсер ещё не подключён (TODO[CA-029b])».
- `real_xltx_test.py:63-64`: удалить `if fmt is SoliqXltxFormat.PROFIT_TAX: pytest.xfail(...)` ветку.
- Grep по репо `TODO[CA-029` — закрыть оставшиеся комментарии (parser.py docstring + parse_manual_input_files.py warning text).

**Verify (full stack):**
- `docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"`.
- **Specifically:** `pytest tests/parsers/real_xltx_test.py -v` — все 23 файла (19 ранее зелёных + 5 PROFIT_TAX) pass.

### Commit 5 — `docs(internal): T2.3 status sync + CA-DS25 claim correction`

- `CLAUDE.md` Current Status: add «T2.3 (PROFIT_TAX parser) complete YYYY-MM-DD» секцию сверху, описать closure 5 xfail + scope.
- `CLAUDE.md` Pre-Demo Roadmap section: T2.3 → DONE, Active → T2.1.
- `docs/pre-demo-roadmap.md`:
  - T2.3 секция → ✅ DONE с deliverables list.
  - Удалить «Замыкает CA-DS25 (KPI sparkline) как side-effect» из строки 207 — реплейс на «Закрывает 5 xfail в `tests/parsers/real_xltx_test.py`, полный 5/5 format coverage парсера».
  - Heads-up «**CA-DS25 sparkline** остаётся frozen — pre-condition не выполнен T2.3, нужен monthly_turnover источник (VAT_DECL chain или ESF, не PROFIT_TAX)».
- `docs/pre-demo-roadmap.md:235` (заблокированные): CA-DS25 pre-condition обновить — «monthly_turnover≥12 источник (VAT_DECL chain / ESF), не T2.3 PROFIT_TAX». Заметка для следующей сессии при планировании T2.4 / backlog.

## Risks & heads-up

- **Q1/Q2/Q3 layout drift** — L36 в Q1-фикстуре содержит мусор (233801 вместо 15). Текущий план не парсит ничего из quarterly. Если позже понадобится quarterly profit_tax bucket — нужны отдельные coordinates per period_index. Backlog T2.x.
- **L46 «к уплате»** не используем сейчас (None в Q1, semantic gap с «начислено»). Если ревью попросит — extend DTO + wire в отдельное поле `tax_payable_by_year` (новый коммит).
- **Cross-source конфликт** PROFIT_TAX vs FORM_2 G30: FORM_2 G30 (`profit_tax_current`) сейчас НЕ доходит до `taxes_paid_by_year` в `_merge_form2`. PROFIT_TAX становится единственным источником для `taxes_paid_by_year`. **Heads-up**: если в будущем FORM_2 G30 захотим тоже мерджить — нужен tier priority (PROFIT_TAX > FORM_2 G30, поскольку Soliq налоговая декларация authoritative для tax computation).
- **CA-027 option b** соблюдена — только Q4 в annual maps, mirror FORM_2.
- **Single source per year** — `_set_once` достаточно, без `_Form2SourceTier`. Если завтра прибавится альтернативный source (FORM_2 G30 merge) — рефакторим в tier.

## Verify command (T2.3 end-state)

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest tests/parsers/real_xltx_test.py -v && uv run python -m pytest src/infrastructure/adapters/soliq_xltx/ src/application/ -v"
```

Pass criteria:
1. 5 PROFIT_TAX fixtures pass без warnings, без xfail.
2. 19 ранее зелёных fixtures продолжают pass.
3. Unit profit_tax_parser_test: 6 кейсов green.
4. Use-case parse_manual_input_files_test: PROFIT_TAX-specific кейсы green.
5. ruff + mypy strict clean.

## Out of scope (явно)

- L46 payable wiring → backlog.
- Cross-validate FORM_2 vs PROFIT_TAX rule → backlog.
- Quarterly PROFIT_TAX bucket → backlog.
- CA-DS25 sparkline → frozen (отдельный pre-condition).
- Tax rate / taxable_income в DTO → YAGNI, extend если потребуется.
