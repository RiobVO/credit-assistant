# ADR-0015 — PDF localization strategy (RU + UZ)

**Status:** Accepted · **Date:** 2026-05-18 · **Context:** T0.4 (Pre-Demo Roadmap)

## Context

T0.4 (UZ-локализация PDF, CA-DS29-pdf) — последний deal-breaker Tier 0 перед bank demo. Узбекское банковское регулирование (НК РУз, Закон РУз «О государственном языке») и compliance-практика требуют: документы кредитного решения должны быть доступны на государственном языке. Сейчас PDF досье — RU-only (templates / pdf_renderer / template_filters / chart_renderer / observations_builder hardcoded на RU).

Frontend локализация уже закрыта в CA-DS29 (`next-intl` runtime switcher, cookie `ca_locale`, keys в `web/src/i18n/{ru,uz}.json`). PDF — отдельный artefact: server-side render через WeasyPrint + Jinja2 + matplotlib, не имеет доступа к frontend i18n context.

Аудит RU-вхождений в backend (на момент написания ADR):

| Файл | RU-вхождений | Природа |
|---|---|---|
| `dossier.html` (Jinja2) | ~115 | Заголовки секций A–F, табличные header'ы, cover labels |
| `pdf_renderer.py` | 116 | `recommendation_label`, severity labels, region-tile, KPI tile titles |
| `template_filters.py` | 55 | Суффиксы валюты, форматтеры |
| `observations_builder.py` | hardcoded f-strings | Strengths/risks head/num/ctx — строится **в Python**, попадает в Jinja как plain text |
| `chart_renderer.py` | 50 | matplotlib axes labels (PNG fallback) |
| `config/rules/v1_uz_msb.yaml` | 19 правил | `name` существующий, `name_uz` отсутствует |

Локализация не сводится «к шаблонам»: `observations_builder.py` собирает строки до Jinja через f-strings, их нельзя оставить «только в template».

Альтернативы рассмотрены:

- **(a) Python-side `gettext`** — стандарт de facto. Workflow: `.pot` / `.po` / `.mo`, инструменты `xgettext` / `msgfmt` / babel extract. Требует tooling и CI-шаг для compilation.
- **(b) Template-level dict** — JSON-файлы `config/pdf-i18n/{ru,uz}.json`, loader как singleton (зеркалит `infrastructure/catalog/` Batch 1A), `messages` injection в Jinja-context + в `build_observations` / `chart_renderer` / `pdf_renderer`.
- **(c) Branchless conditionals в template** — `{{ rule.name_ru if lang == 'ru' else rule.name_uz }}`. Подходит только для 1-way switch'ей на структурированных данных (rule.name); не масштабируется на сотню template strings.

## Decision

**Гибрид (b) + (c):**

1. **Template strings + Python labels + observation templates** → `(b) template-level dict`.
   - JSON-конфиги `config/pdf-i18n/{ru,uz}.json` — единый keyspace для обеих локалей.
   - DTO `application/dto/pdf_messages.py` (`PdfMessages` frozen dataclass).
   - Loader `infrastructure/i18n/pdf_messages.py` с `@lru_cache(maxsize=2)`.
   - Injection: `RenderDossierPdf.__init__(..., pdf_messages_loader: Callable[[str], PdfMessages])`, `execute(dossier_id, lang)`.
   - В Jinja-context: `{{ t.section_a_title }}` (alias `t = messages` для terseness в template).
   - В `build_observations(..., messages: PdfMessages)`: f-strings заменяются на `messages.observation_revenue_growth_head.format(pct=...)` — структурированные format strings.
   - В Jinja filters (`fmt_money`, `fmt_pct`) — closure-инжект: `env.filters["fmt_money"] = make_fmt_money(messages)` при build environment. Filters не теряют параметризацию.
   - В `chart_renderer.render_revenue_chart(..., messages)` — axes labels через `messages.chart_axis_revenue` и т.д.

2. **`rule.name`** → `(c) branchless conditional`.
   - В `domain/rules/rule.py`: `Rule.name_uz: str` рядом с `name: str` (де-факто `name_ru`).
   - В `config/rules/v*.yaml`: каждое правило получает `name_uz` (required, `min_length=1`).
   - В template F-секции: `{{ rule.name_uz if lang == 'uz' else rule.name_ru }}` (или alias `rule.name` для RU как default).
   - Rule names — не template chrome, а structured data: branchless 1-way switch проще, чем дублировать 19 keys в pdf-i18n JSON.

3. **Endpoint contract.**
   - `GET /api/dossier/{id}/pdf?lang=ru|uz` — query param опциональный.
   - Fallback chain: `query.lang → brand.default_lang → "ru"`.
   - `BrandConfig.default_lang: str | None = None` — новое опциональное поле в `config/brands/<id>.json` (uzbekbank получает `"defaultLang": "uz"` через отдельный таск, не в этом коммите).
   - Audit-log `download_pdf` payload получает `{"lang": <resolved>}`.

4. **Domain schema.** `RuleSpecYaml.name_uz: str = Field(min_length=1)` — required. Без soft fallback. Banking-grade продукт не должен иметь fallback-to-empty semantics; новое правило без UZ-имени → schema fails on load_registry, не на runtime в PDF.

## Rationale

**Почему не gettext (a):**

- **Tooling overhead.** `.pot` extraction / `.po` translation / `.mo` compilation требуют 3 инструмента (xgettext, poedit/manually, msgfmt). Для 2 локалей и ~80 уникальных строк gettext — преждевременная оптимизация.
- **CI integration**. Build pipeline должен компилировать `.mo` при каждом deploy. Docker layer caching усложняется.
- **Прецедент в проекте отсутствует.** Frontend использует JSON dict (`next-intl`). Backend reference catalog'и (`infrastructure/catalog/`, OKVED + USD rate) — JSON. Gettext добавил бы третий стиль.

**Почему JSON dict (b) предпочтительнее:**

- **Mirror frontend.** `web/src/i18n/{ru,uz}.json` — тот же mental model. Один engineer'ский паттерн на проект.
- **Mirror catalog pattern.** `config/okved/`, `config/exchange/` уже JSON + DTO + loader. PDF-i18n зеркалит этот pattern буква-в-букву.
- **No tooling.** Plain JSON редактируется в любом editor'е, diff-friendly, mergeable.
- **lru_cache identity.** Loader singleton (`@lru_cache(maxsize=2)`, по ключу locale) исключает повторное чтение / парсинг при каждом render.

**Почему branchless для rule.name (c):**

- **Structured data, не chrome.** `rule.name_ru` / `rule.name_uz` живут вместе с правилом в YAML, version-locked к `rule.version`. Дублировать 19 keys в pdf-i18n JSON — расщеплять single source of truth.
- **Тривиальный 1-way switch.** Без message format / pluralization / interpolation. `if/else` — самый честный код для этой формы.
- **Audit-friendly.** Аудитор видит rule.name рядом с rule_id в одном файле, не прыгает между `v1_uz_msb.yaml` и `pdf-i18n/uz.json`.

**Почему `name_uz` required в schema:**

- Banking compliance: каждое сработавшее правило должно быть читаемо на гос. языке. Empty `name_uz` = баг до банкира.
- Schema validation = fail-fast on load_registry (startup), не на runtime PDF generation. Лучше падать рано.
- `min_length=1` ловит и empty string, и пропущенный ключ. YAML mid_length-validation бесплатна через Pydantic.

**Почему `lang` пробрасывается через use-case, не resolves в template:**

- Domain / application слои чисты от Locale enum'ов (`str` Literal достаточен) — нет coupling с infrastructure i18n.
- Template получает финальный `messages: PdfMessages` + `lang: str` — без re-resolution. Single source of truth.

## Trade-offs

- **JSON dict не масштабируется на ICU MessageFormat (plural / gender / select).** Узбекский имеет 2 plural forms (singular / plural same as Russian), пока pluralization не нужна; если потребуется — миграция на ICU library (`PyICU` / `babel.support.LazyProxy`) — отдельный ADR.
- **Format strings vs full template inversion.** `observations_builder` после refactor'а имеет `messages.observation_revenue_growth_head.format(pct=..., year=...)` — placeholder mismatch (опечатка в JSON) ловится только на runtime. Защита: unit tests на обе локали + строгий `.format()` (не `.format_map()`) роняет на missing-key.
- **`name_uz` required ломает existing inline-YAML test fixtures.** Mitigation: одна миграция в commit 3 — все fixtures получают `name_uz` за один проход, schema validation выявляет пропущенные cases на CI.
- **Closure-injected Jinja filters** (`make_fmt_money(messages)`) — filter registry становится environment-scoped, не module-level singleton. Если env создаётся per-render — overhead приемлем. Если env shared (наш случай — `WeasyPrintPdfRenderer` singleton), filters перестраиваются при каждом render-call с разной локалью. Acceptable: rebuild стоит микросекунды.
- **Chart rendering (matplotlib)** не использует Jinja messages напрямую — `render_revenue_chart` принимает `messages` параметром. Если в будущем добавится третья локаль (карак., туркм.), сигнатура расширится в одной точке.

## Consequences

- **`Rule` теряет «name = canonical RU»**: после refactor'а `rule.name` остаётся синонимом `rule.name_ru` для обратной совместимости с observations_builder (где используется как fallback в RU-ветке). Phase B (post-demo): возможно переименовать в `name_ru` явно — ADR на отдельной итерации.
- **Snapshot mapper roundtrip не задеваем** (verified 2026-05-17, `dossier_mapper.py:15-28` сериализует только `rule_id` + `rule_version`). Existing dossier snapshots в БД при rebuild PDF на UZ берут `rule.name_uz` из live registry — это correct semantic (rule version stays same, locale display refreshes).
- **PDF endpoint становится bilingual за один query param.** Frontend (CA-DS29 cookie `ca_locale`) → server action transmits cookie value в `?lang=` при download PDF — отдельный таск (T0.4 endpoint + frontend wire-up).
- **uzbekbank brand-config получит `defaultLang: "uz"`** в последующем коммите (демо-ready). default.json остаётся без `defaultLang` (fallback на "ru").

## Implementation reference

T0.4 декомпозиция (8 коммитов):

1. **ADR-0015** (этот документ).
2. **Domain**: `Rule.name_uz` + `RuleSpecYaml.name_uz` (required) + `registry_factory` пробрасывает.
3. **YAML migration**: `config/rules/v1_uz_msb.yaml` получает `name_uz` для 19 правил (manual UZ перевод).
4. **i18n infra**: `config/pdf-i18n/{ru,uz}.json` + `application/dto/pdf_messages.py` + `infrastructure/i18n/pdf_messages.py` (loader + lru_cache).
5. **Use case**: `RenderDossierPdf.execute(dossier_id, lang)` + `DossierPdfBundle.lang` + `.messages`.
6. **Observations rewrite**: `build_observations(..., messages)` — f-strings → `messages.X.format(...)`.
7. **Templates + Python labels**: dossier.html / pdf_renderer / template_filters / chart_renderer переходят на `messages` injection.
8. **Endpoint**: `?lang=` query param + `BrandConfig.default_lang` fallback + audit-log payload.

Roadmap update — отдельным финальным коммитом после passing verify.
