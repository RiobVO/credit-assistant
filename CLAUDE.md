# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус, открытые задачи и рабочие соглашения.
> Историческая глубина: `docs/session-log.md` (полная история), `docs/design-sweep-archive.md` (per-phase narrative), `docs/operations/` (smoke-guides).

---

## Current Status

**Phase 10 (PDF document) закрыта 2026-05-15** (`a8f2b66`). Финальная фаза Design Sweep — credit memorandum aesthetic для banking output. Cover: hero decision-block (gauge 200pt + recommendation 28pt + signal breakdown inline) + decision-meta full-width + observations pros/cons split (3 strengths + 3 risks). Section A redesign: identity hero с auto-derived avatar (initials) + 3 stat tiles (Возраст · Регион · ОКВЭД) + clean detail rows. Brand-tenant: `BRAND_ID` env → `config/brands/<id>.json` через `infrastructure/brand/`. ГНК pill убран физически (Phase 9 lesson). F-секция: human-readable `rule.name` из YAML вместо rule_id. Observations builder (`application/services/`) — strengths из позитивных KPI + risks из top-3 red flags severity-sorted. CI `25934169074` → ~1m.

**Дизайн-pass завершён:** все 10 фаз DONE. Следующие итерации — backlog TODO (CA-DS6/7/8/14-25/28, CA-003/015/019-020/028/029b/064/DS11).

**Активная ветка:** `main`.

---

## Открытые TODO

### Backend / data
- **CA-003**: реальный лукап ГНК для ИНН (см. CA-DS28 для hybrid roadmap).
- **CA-015**: уточнить `vat_declaration_parser.py` под живые xltx 10006_45/10006_47.
- **CA-019**: refresh-token rotation + denylist (Redis) — в v1 stateless 7д.
- **CA-020**: LDAP/OAuth AuthnAdapter для production-банка. `AuthnPort` готов.
- **CA-028**: dynamic unit detection для FORM_2 — сейчас hardcoded ×1000.
- **CA-029b**: парсер PROFIT_TAX (taxes_paid, 15 листов). Adapter raises UnsupportedFormatError.
- **CA-064**: ship `error.tsx` в real observability (Sentry / posthog).
- **CA-DS11**: faktura.uz API integration. Сейчас сервис в `/api/system/health` всегда `not_implemented`.

### Design Sweep tail
- **CA-DS6** (help): вынести `support` section в `brand-config.json` (phone/email/Slack/Docs/compliance_phone).
- **CA-DS7** (help): backend-endpoint для real operator-shift presence.
- **CA-DS8** (help): отдельный compliance-phone в brand-config.
- **CA-DS14**: `/help` секция «Что делать при смене телефона» — MS Authenticator iCloud-cache scenario.
- **CA-DS15**: рассмотреть WebAuthn/Passkeys как alternative 2FA-фактор.
- **CA-DS16**: убрать legacy stored bool `analysts.mfa_enabled` через миграцию.
- **CA-DS17**: real OKVED-каталог из backend-endpoint или статичный JSON. Сейчас 16 кодов хардкод.
- **CA-DS18**: реальный `case_id` с бэкенда. Сейчас clientside `Math.random()` placeholder.
- **CA-DS19**: motion cleanup pass по /search и /history (pulse-* на trust-pill + LiveStrip).
- **CA-DS20**: RTL-тесты на InnInput state machine + OkvedAutocomplete.
- **CA-DS21**: `auto-edited` 3-state в source-trail (Step 2). Сейчас 2-state.
- **CA-DS22**: keyboard nav в `CustomDropdown` (Soliq year/month). Сейчас только mouse.
- **CA-DS23**: RTL-тесты на `Step2Financials` source-trail rendering.
- **CA-DS24**: real `/api/system/cbu/usd-rate` или config-driven course вместо hardcoded `USD_RATE_UZS = 12575`.
- **CA-DS25**: real backend sparkline для KPI (EBIT/ROE/Debt-to-EBIT). Нужна monthly-проекция EBIT.
- **CA-DS28**: real ГНК lookup для CA-003 (hybrid: public lookup `soliq.uz/services/search/` + manual upload справки). **Legal review обязателен** (уз-юрист 30 мин + robots.txt check). Pre-condition для CA-003 закрытия.

---

## Активные договорённости (compact)

### Domain / data contracts
- **VAT-периоды** (ADR 0006): `BorrowerSnapshot.vat_periods: list[VatPeriodReport]`. Декларация → `vat_declared`, ilova → `esf_seller_vat_total`. Сравнение в рамках одного налогового периода.
- **ИНН заёмщика**: приходит явно от пользователя, не угадывается из имени файла.
- **xltx форматы (5 типов)**: VAT_DECLARATION (8 листов), VAT_REGISTRY_ILOVA (10, Приложение №4), FORM_2_INCOME_STATEMENT (3), FORM_1_BALANCE_SHEET (4), PROFIT_TAX (15). Distinguished по сигнатурным cells list01.
- **Парсер soliq_xltx best-effort**: raises только на формат (UnsupportedFormatError, XltxBorrowerMismatchError); cell-level → warn + None. Каждый DTO имеет `parse_warnings: list[str]`.
- **Реальные данные папы**: локально в `~/Downloads` / `tests/fixtures/**/*_full.*`, не в git. В repo — `*_sample.csv` + synthetic factory-helpers.

### Persistence / infra
- **Persistence**: testcontainers + real Postgres для integration-тестов; draft TTL = 30d.
- **Compose-postgres** на host **5433** (5432 занят native PG).
- **Windows + asyncpg**: обязателен `WindowsSelectorEventLoopPolicy` (настроено в `migrations/env.py` + `main.py`).
- **Backend в Docker** (ADR 0008): WeasyPrint требует Pango/HarfBuzz/Fontconfig. Compose `api` на 8000. Правки кода → `docker compose up -d --build api`, не `restart` (см. memory `project_docker_crlf_gotcha.md`).
- **Phase 4 — Bank Mode** (ADR-0009): `APP_MODE` env управляет инсталляцией. Bank: shared endpoints закрыты `Depends(get_current_analyst)`. Audit `login/login_failed/logout/search_borrower/view_dossier/generate_dossier/download_pdf` пишется в `audit_log`. `dossiers.source_mode` + nullable FK `created_by_analyst_id`.
- **JWT** (Phase 4.B): native `bcrypt`, HS256, access 15м + refresh 7д без ротации в v1. `JWT_SECRET` через env, мин. 32 байта в проде.
- **Frontend BFF cookies**: httpOnly + sameSite=lax + secure-в-проде. Tokens в `ca_access` (path=`/`) и `ca_refresh` (path=`/api/auth`). Client JS никогда не видит JWT.
- **Seed analyst**: `docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email ... --password ... --full-name ..."`.

### Rules / KPI conventions (изменяешь — обновляй sync)
- **CA-044** Money | None: `FinancialReport.taxes_paid` опциональный сквозь стек. `None` = «не заполнил», `Money(0)` = «осознанно ноль». Frontend mapper `moneyOptional(digits)` → `undefined` при пустой строке.
- **CA-043** `fmt_pct` контракт: принимает значение **уже в процентах** (consistent с kpi_calculator: `(a-b)/b*100`). Не fraction.
- **CA-037** KPI naming: EBIT = `profit_before_tax + interest_expense` (компонент EBITDA без D&A). UI рендерит «EBIT (прокси EBITDA)» + tooltip. Когда D&A появится — добавляем `ebitda` / `debt_to_ebitda` **рядом**, не переименовываем.
- **CA-037** Snapshot JSONB round-trip: новые nullable поля `FinancialReport` сериализуются в JSONB через `_financial_report_to_dict`/`_from_dict`. **Расширяешь FinancialReport новым полем — обязательно добавь в snapshot_mapper и unit-тест round-trip**.
- **CA-047** BalanceSnapshot: 8 балансовых полей сгруппированы в `domain/value_objects/balance_snapshot.py`. Wire contracts остались flat для обратной совместимости.
- **CA-042** FORM_2 tier priority: `header.period_year == year` (CURRENT) > `year + 1` (PRIOR). CURRENT silently перезаписывает PRIOR.
- **CA-049** NEGATIVE_EQUITY rule: critical-severity, на `latest_annual.balance_end.equity ≤ 0`. **Новое правило — обновляй YAML+CODE_RULES синхронно**: `load_registry()` raises на асимметрии.
- **CA-048** KPI threshold coloring: пороги ROE (>15 GOOD / 5-15 WARN / <5 BAD) и Debt/EBIT (<2 / 2-4 / >4) — single source of truth в `kpi_calculator.py`, не дублировать на frontend/PDF.
- **CA-035b** Readiness в готовом досье: GET `/api/dossier/{id}/readiness`. `source_trail` в БД не хранится; `infer_parser_sources_from_snapshot` heuristic.

### Frontend conventions
- **CA-053** strict-mode useEffect: `cancelled`-guards в `.finally()` опасны для terminal UI-flags (loading/error). Для UI-flags `setIsLoading(false)` ставь безусловно.
- **CA-058** prefill Шага 1: при «Пересобрать с дополнениями» — borrower-карточка через sessionStorage (`ca:manual-input-prefill-step1`). Финансы и кредит остаются defaults.
- **CA-060** Design tokens (ADR-0011): один design system, brand-tenant через `config/brands/<id>.json`. Semantic слой в `globals.css`: `--surface/-2/-3`, `--ink-1..4`, `--state-{ok,warn,bad,info,neutral}-{fg,bg,border}`, `--brand-primary/-hover/-soft/-ink/-ring`. Chart-палитра 9 токенов.
- **CA-061** mode-conditional (ADR-0011): `if (mode === "bank")` запрещён глубже top-level shells. Хук `useAppMode()` (`web/src/lib/use-app-mode.ts`) — единственная точка для client-shells.
- **CA-062** ESLint hex guard: `no-restricted-syntax` для `src/features/**` + `src/components/**`. **Не ловит** Tailwind utility `bg-[#XXXXXX]` — ручная гигиена.
- **CA-063** i18n infra: `next-intl` 4.4.1, статичная локаль через `NEXT_PUBLIC_LOCALE`, keys в `web/src/i18n/{ru,uz}.json` (keyspace `shared/bank/accountant/dossier`). RTL-тесты обёртывать в `<NextIntlClientProvider locale="ru" messages={ru}>`. **Brand-strings (имена, теглайны) не локализуются** — это tenant-config.
- **CA-066** brand-context client-side: server `resolveBrand()` + `<html data-brand>` + `BrandProvider` + `useBrand()` (`web/src/lib/brand-context.tsx`). Tagline в brand-config — **полная** строка.
- **CA-066** `t.rich` gotcha: для ReactNode-обёртки message **обязан** иметь tag-плейсхолдер `<x></x>`, не value `{x}`. Иначе «Functions are not valid as a React child».
- **Phase 8 SectionCard / CounterChip / StaticPill** (`web/src/components/section-card.tsx`): shared shell — wizard передаёт `icon`, dossier нет (header grid схлопывается). Visual-only, без i18n bindings. **Не дублировать pattern локально** — 10+ consumer'ов через shared.
- **Phase 7 source-trail UI** (Step 2): 2-state — `auto` (зелёный borderbar) / `manual` (серый), плюс спец `manual-required` (amber для taxesPaid). Borderbar реализован как `absolute span` (не CSS-border — мешает UZS-suffix).
- **Phase 10 PDF brand-tenant**: `BRAND_ID` env → `config/brands/<id>.json` через `infrastructure/brand/`. `BrandConfig` dataclass в `application/dto/` (clean architecture — pure), loader в `infrastructure/`. Backend mirror фронтового `resolveBrand()`, single source of truth — JSON в `config/brands/`. Шрифты PDF строго bundled 400/500/600/700 (no 800 — fallback в WeasyPrint).
- **Phase 10 Observations builder** (`application/services/observations_builder.py`): cover bottom half. Strengths derived from positive KPI: revenue growth · ROE≥GOOD · positive net profit · low debt (cap 3). Risks = top-3 red flags by severity (critical → high → medium → low). Rule name lookup через `RuleRegistry.by_id(rule_id).name` из YAML.
- **Phase 10 Rule.name field**: добавлено в `domain/rules/rule.py`, пробрасывается через `registry_factory` синхронно с `config/rules/v*.yaml`. PDF F-секция рендерит human-readable name; rule_id остаётся в `.src` строке как technical reference для аудитора.

---

## Design Sweep status

| # | Phase | Status | Commit |
|---|---|---|---|
| 1 | Login | DONE | `0a1c86c`..`34d97f6` |
| 2 | Search | DONE | `c9afbce` → `022dfcf` |
| 3 | History | DONE | `8bbc154` |
| 4 | Help | DONE | `cb8b046`..`91c4090` |
| 5 | Settings | DONE | `06f0ae4` + Phase 5.B + functional holes |
| 6 | Manual-input Step 1 (Borrower) | DONE | `d2fb869` + `c116908` |
| 7 | Manual-input Step 2 (Financial) | DONE | `40c770d` |
| 8 | Manual-input Step 3 (Loan) | DONE | `94229e8` |
| 9 | Dossier view | DONE | `bcde558` |
| 10 | PDF document | DONE | `a8f2b66` |

Подробности по каждой фазе — `docs/design-sweep-archive.md`.

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns).
- Plan mode обязателен если затрагивается >2 файлов.
- Не начинай кодить без плана — сначала покажи декомпозицию.
- Язык UI: русский. Язык кода: английский.
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- **В commit messages никогда не упоминать `claude` / `AI` / `assistant` / `agent` / `LLM` / `GPT`** — ни в subject, ни в body, ни в scope. Для коммитов трогающих `CLAUDE.md` использовать scope `docs(rules)` / `docs(internal)` / `docs(arch)`, не `docs(claude)`. Commits должны читаться как написанные мной вручную.
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`).
- После `git mv` + правок (sed/Edit) обязателен `git add -u` или явный re-add (см. memory `feedback_git_mv_sed_gotcha.md`).

### Pre-push checklist

Перед `git push` прогнать **полный** verify:

1. **`npm ci` ≠ `npm install`**. После добавления зависимости — `rm -rf node_modules package-lock.json && npm install`, потом `npm ci` локально чтобы воспроизвести CI-режим.
2. **`ruff check` + `mypy --strict` + `pytest`** обязательны перед push. Минимум: `docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"`.
3. **Меняешь computed-from-X invariant — `grep -r` все тесты на эту semantic.** Локальный mapper-test может пропустить интеграционный тест.
4. **CI коммита перед твоим зелёный?** `gh run list --branch main -L 3` перед началом работы.

---

## Architecture Reminders

- `domain/` не знает про `infrastructure/` — никогда.
- Все бизнес-правила — только в `domain/rules/`, ссылка на источник обязательна.
- Новый банк = новый adapter, не правки в ядре.
- Two modes (Bank / Accountant) — два UI поверх одного бизнес-ядра.

---

## Security Hard Rules

- Данные заёмщиков не логируются.
- Никаких внешних API в production (только on-premise).
- Soliq данные — только через официальный экспорт/API, не scraping (исключение — публичный лукап `soliq.uz/services/search/` после legal review, см. CA-DS28).
- `.env` не в git, secrets через Vault в production.

---

## Operations playbooks

- **2FA smoke (4 пути, ~10 мин)** — `docs/operations/2fa-smoke.md`.

---

## Start of Session Command

```
Прочитай @PROJECT_BRIEF.md целиком, потом @CLAUDE.md.
Скажи на каком phase мы сейчас и какая следующая atomic задача.
Не начинай кодить — сначала покажи план.
```

Если нужна историческая глубина:
- `docs/session-log.md` — полная хронологическая история по сессиям с commit hashes
- `docs/design-sweep-archive.md` — детали Phase 1-9 (preview HTML, иттерации, lessons)
- `docs/operations/2fa-smoke.md` — пошаговая инструкция smoke 2FA
- `docs/adr/` — Architecture Decision Records (0001..0011)
