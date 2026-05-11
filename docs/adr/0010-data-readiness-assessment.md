## ADR 0010: Data Readiness Assessment service

- **Status**: Accepted
- **Date**: 2026-05-12
- **Phase**: post-4 (CA-035)

## Context

Чек-лист «Перед отправкой на скоринг» в Шаге 3 wizard'а (Accountant Mode) и
аналогичные индикаторы в банковском режиме / PDF досье должны единообразно
отвечать на вопрос «достаточно ли данных для скоринга». Реализация в
`step-3-loan.tsx` к моменту CA-035 содержала два кривых пункта:

1. Счётчик «X / 24» итерировал только `q1..q4`, игнорировал autofilled
   annual cells (CA-027 FORM_2 Q4 пишет в `annual`) — пользователь грузит
   FORM_2, видит `0/24` и думает что autofill не сработал.
2. Пункт «Активы и обязательства соответствуют форме №1» ставил зелёную
   галку при наличии manual-введённых `totalAssets/totalLiabilities`, без
   подтверждения от парсера FORM_1 — фейковая ✅.

Латать локальную логику в одном компоненте создавало долг: та же оценка
«готовности данных» нужна downstream:

- CA-037 (KPI EBITDA/ROE/Debt-to-EBITDA — нужны FORM_1 + 2 года выручки);
- CA-032 (ESF aggregation — нужно знать когда tax burden ratio доступен);
- Bank-mode pre-check на этапе поиска;
- PDF досье (показать «доверие к данным: 75%»).

## Decision

Выделить **Data Readiness Assessment** как pure domain service с
4-уровневой шкалой готовности + независимым списком missing_capabilities +
confidence_score ∈ [0, 1]. Потреблять через stateless POST endpoint
`/api/manual-input/readiness` для draft (Шаг 3 wizard) и GET
`/api/dossier/{id}/readiness` для досье (отложено в CA-035b).

### Слой 1 — Domain (`src/domain/services/data_readiness.py`)

```python
class DataReadinessLevel(StrEnum):
    INSUFFICIENT = "insufficient"   # < 1 полного года выручки
    MINIMAL      = "minimal"        # 1 полный год
    STANDARD     = "standard"       # ≥2 года подряд
    COMPREHENSIVE = "comprehensive" # ≥3 года подряд + FORM_1 + (ESF_CSV OR PROFIT_TAX)

class ParserSource(StrEnum):
    FORM_2, FORM_1, VAT_DECLARATION, ESF_CSV, PROFIT_TAX, MANUAL

@dataclass(frozen=True, slots=True)
class DataReadinessReport:
    level: DataReadinessLevel
    years_covered: tuple[int, ...]
    full_years: tuple[int, ...]
    missing_capabilities: tuple[str, ...]
    parser_sources: frozenset[ParserSource]
    confidence_score: Decimal

def assess_readiness(snapshot: BorrowerSnapshot, sources: set[ParserSource]) -> DataReadinessReport
```

Правила:
- «Полный год» = annual report за этот календарный год OR ≥4 квартальных
  reports за тот же year (по `period.end.year`).
- COMPREHENSIVE требует **3 года подряд** (consecutive — серия в наборе),
  FORM_1 в sources, хотя бы один tax-источник (ESF или PROFIT_TAX).
- Capabilities derive независимо от level:
  - `yoy_trend` missing если consecutive_max < 2
  - `cagr` missing если consecutive_max < 3
  - `balance_ratios` missing если FORM_1 не в sources
  - `tax_burden` missing если ни ESF, ни PROFIT_TAX не в sources
- `confidence_score = min(1.0, 0.25·N_full_years + 0.15·[FORM_1] + 0.10·[tax_source])`

Domain pure: никакого I/O, без зависимости от persistence/interfaces.

### Слой 2 — Application (`src/application/use_cases/assess_draft_readiness.py`)

Stateless оркестратор для **draft path** (Шаг 3 wizard):

```python
@dataclass(frozen=True, slots=True)
class AssessDraftReadinessInput:
    annual_report_years: list[int]
    full_quarter_years: list[int]
    partial_quarter_years: list[int]
    source_trail: dict[str, str]

def assess_draft_readiness(payload) -> DataReadinessReport
```

Принимает **аналитический срез form state**, а не raw form payload. Frontend
сам derives «годы с annual / full quarters / partial quarters» из watched
form values — он точнее знает структуру формы и реактивно обновляется на
keystroke. Backend получает уже агрегированную картину и строит синтетический
`BorrowerSnapshot` с минимально-валидными FinancialReport-ами (revenue=1
UZS — placeholder), на котором domain.assess_readiness работает без модификаций.

`source_trail_to_parser_sources()` маппит ключи CA-027 dropzone в
`set[ParserSource]` по префиксам: `form1.*` → FORM_1, `revenue_/net_profit_`
→ FORM_2, `vat_declared_` → VAT_DECLARATION, `esf_` → ESF_CSV, `profit_tax_`
→ PROFIT_TAX. Незнакомые keys silently ignored (future-proof).

### Слой 3 — Interfaces (`src/interfaces/api/shared/data_readiness.py`)

`POST /api/manual-input/readiness` — stateless evaluation. Mount в обоих
режимах (bank — за `Depends(get_current_analyst)`, accountant — открыт).

Pydantic schema:
- `DataReadinessRequest{annual_report_years, full_quarter_years,
  partial_quarter_years, source_trail}` (все optional, default `[]`/`{}`)
- `DataReadinessResponse{level, years_covered, full_years,
  missing_capabilities, parser_sources, confidence_score}` (Decimal как
  строка без хвостовых нулей через `_format_decimal`)

### Слой 4 — Frontend (`web/src/app/(accountant)/manual-input/`)

- `_hooks/use-source-trail.tsx`: React Context Provider для UI-only
  source_trail из CA-027 dropzone. **Не form state** — source_trail не часть
  «контракта формы» и не идёт в финальный POST /api/manual-input.
- `_components/checklist.tsx` (extract из `step-3-loan.tsx`): watches step2
  form, debounce 500ms, useQuery POST /readiness, рендерит tri-state pill
  + missing_capabilities как inline sub-rows.
- `lib/api.ts`: `assessReadiness()` client + TypeScript типы.

### Слой 5 — Docs

Этот ADR + Session Log в CLAUDE.md + TODO[CA-035b] (GET
`/api/dossier/{id}/readiness` для досье/PDF wiring).

## Why stateless POST for draft (not GET with draft_id)

Альтернатива: GET `/api/manual-input/draft/{id}/readiness` с persisted
draft. Отвергнута:

- Существующий `useFormDraft` сохраняет draft только на переход между
  шагами, не on-input. GET даст устаревшие данные пока пользователь
  печатает в Шаге 3 (или меняет step2 без перехода). UX отстаёт.
- Решение через autosave-on-input + persist source_trail в draft требует
  миграцию `drafts` table + autosave hook + conflict handling. Раздувает
  scope CA-035 с UI fix до infra change.
- Stateless POST с inline body не имеет проблемы рассинхрона: frontend
  владеет form state, в каждый запрос шлёт текущее состояние.
- Для dossier path (CA-035b) — GET имеет смысл: dossier persisted,
  snapshot стабилен.

## Why analytical slice (not raw form payload)

Альтернатива: фронт шлёт raw `ManualInputPayload` (как в финальном POST
/api/manual-input), бэк строит chunks → snapshot через существующий
`build_borrower_snapshot`. Отвергнута:

- `ManualInputRequest` валидируется Pydantic'ом со строгими invariants
  (валидный 9-значный ИНН, обязательный borrower) — partial draft на
  Шаге 2 не проходит.
- Frontend лучше знает структуру своей формы и какие именно cells
  заполнены (например `annual` vs `q1..q4`, частичные quarters). Дублировать
  эту логику на бэкенде = source of bugs.
- Аналитический срез (3 списка int + dict) — узкий contract, тривиально
  тестируется, не привязан к конкретной форме wizard'а.

## Why React Context for source_trail (not form state)

Отвергнуто хранение `source_trail` как `step2.autofillSources` в zod
schema:

- source_trail — UI-only memory (label «откуда взяли значение»), не
  «контракт формы» — он не идёт в финальный POST /api/manual-input.
- Form state замусоривается non-form-data, draft persistence начинает
  носить лишний JSON.
- React Context даёт чистое разделение: form schema = что пользователь
  ввёл, context = откуда мы это поняли. Один Provider в `manual-input/page.tsx`,
  setter в dropzone, reader в checklist — три callsite, никакого invasive
  рефактора.

## Consequences

### Positive

- Domain pure, переиспользуется для draft / dossier / PDF / scoring без
  изменений в правилах оценки готовности.
- Frontend владеет UX-логикой «что считать заполненным» — реагирует
  мгновенно, не зависит от round-trip к persistence.
- 4-уровневая шкала + список missing_capabilities — richer чем boolean,
  даёт UI основание для конкретных amber-сносок «YoY недоступен» вместо
  generic «не готово».
- COMPREHENSIVE как явный target — пользователь видит чего не хватает до
  лучшего скоринга (FORM_1, ESF / PROFIT_TAX).

### Negative

- Дублирование «definition of full year» между frontend (`hasAnyQuarterValue`
  + checklist analytical-slice builder) и backend domain (`_full_years`).
  Trade-off: frontend знает форму, backend знает domain — каждый делает
  своё, контракт `int → year` тривиальный.
- Stateless POST не оставляет audit trail «когда чек-лист был зелёный».
  Для bank install — TBD: audit-wiring в use case можно подключить если
  понадобится (CA-035b может расширить).
- `confidence_score` — эвристика с round numbers (0.25 / 0.15 / 0.10),
  не основана на статистике. Пересмотр после первых месяцев pilot'а.

## Out of scope (отложенные тикеты)

- **CA-035b**: GET `/api/dossier/{id}/readiness` — domain готов, нужен
  application use case + interfaces wiring + frontend consumer в досье/PDF.
- **CA-040**: vitest + @testing-library setup для frontend; туда же —
  unit-тесты `checklist.tsx` и `useSourceTrail`.
- **Wiring FORM_1 в `/api/manual-input/parse-files`**: парсер FORM_1
  реализован в CA-029a, но `parse_manual_input_files` use case не
  использует его (emits warning). После wiring `form1.assets_total` /
  `form1.liabilities_total` начнут попадать в source_trail и unlock
  COMPREHENSIVE для пользователей с полным набором.

## Tests

- 51 unit-тест domain (`data_readiness_test.py`) — все 4 уровня, ветки
  consecutive_max, missing_capabilities mapping, confidence_score boundary,
  edge cases (frozenset input, immutable report, gaps).
- 17 unit-тестов application (`assess_draft_readiness_test.py`) — все 6
  префиксов source_trail mapping, unknown keys ignored, level transitions.
- 7 integration-тестов (`tests/integration/api/data_readiness_test.py`) —
  POST endpoint, все 4 уровня, partial quarters, StrictModel rejection.
- Frontend unit-тесты — TODO[CA-040].

## References

- CA-027 (multi-file autofill): `5a5f395`, `659440d`
- CA-029a (FORM_1 parser): `2bf833b`
- CA-033 (pre-score null state): `96e53e4`
- CA-035 commits: `a070f3f` (domain), `2a97a90` (application),
  `ff8f585` (interfaces), `642fa60` (frontend)
