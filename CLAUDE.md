# CLAUDE.md

> **⚠️ ОБЯЗАТЕЛЬНАЯ БУТСТРАП-ДИРЕКТИВА (читается моделью первой):**
> ПРЕЖДЕ чем отвечать на ЛЮБОЙ вопрос пользователя об этом проекте — будь
> это «что нам надо сделать?», «какие открытые задачи?», просьба о
> code-change или просто пояснение — ты ОБЯЗАН прочитать
> `docs/conventions/active-contracts.md`. Это не опционально и не зависит
> от того, упомянул ли пользователь этот файл явно. Без него ты не знаешь
> живые domain / persistence / rules-KPI / PDF i18n / frontend контракты
> (CA-001..CA-070+) и сломаешь инварианты. Сначала read, потом ответ.
>
> Также читай `PROJECT_BRIEF.md` (если не читал в текущей сессии) для
> бизнес-контекста и архитектуры.
>
> История по сессиям/дням — `docs/session-log.md`. UI sweep narrative —
> `docs/design-sweep-archive.md`. Smoke playbooks — `docs/operations/`.
> Architecture decisions — `docs/adr/` (0001..0024).

---

## Current Status (2026-05-20)

**Pre-demo MVP ready** (closed 2026-05-18, Tiers 0/1/2/3 complete).
**ADR-0024 Day 4 closed** (PR #14 + #13 + #12 → main `2be6ea2`):
OKVED→ОКЭД atomic rename (Alembic `b04677374b85`), 8-й KPI
`fx_exposure_ratio` (без level_tone v1, CA-070), `CIRCULAR_INVOICING`
via networkx (3+ node ready, CA-002 closed → CA-002b deferred).
Rule count 24, KPI 8. Готов к Day 5 — Pre-demo smoke walkthrough.

История сессий/дней — `docs/session-log.md` (S1/S2/S3/Day 4 с PR refs +
commit hashes + lessons).

### Runtime state

- Docker compose: `credit-api` (8000), `credit-postgres` (5433), `credit-redis` (6379) — все healthy. `credit-db-backup` sidecar smoke'нут (PASS exit=0).
- Backend env: `APP_MODE=bank`, `BRAND_ID=default`, `PII_ENC_KEYS` задан тестовым Fernet-ключом (`/tmp/pii_key.txt`, prefix `iEuuP5WADM_...`). БД зашифрована — без ключа restore из `backup-pre-t13.sql` (gitignored).
- Frontend Next dev (Turbopack) `npm run dev` в `web/` — порт 3000. Production-image тоже билдится (T3.6.1).
- Seeded analyst для smoke: **email `t04@bank.uz`** / **password `T04Smoke!`**, без MFA.
- Dossiers: 52 (47 backfilled `BR-2026-0001..0047` + smoke `BR-2026-0048..0049` + 3 post-Day-4 smoke iterations `BR-2026-0050..0052`). Snapshot.payload + drafts.payload зашифрованы. Demo scenarios используют `BR-2026-0030/0040/0042/0046/0047` (см. `docs/demo/scenarios.md`).
- Independent audit 2026-05-21 — `docs/audit/2026-05-21/00-summary.md` (5 параллельных subagent'ов: honesty / security / architecture / demo-readiness / documentation, area scores 5/10–8.5/10, top-10 фиксов priority-ranked).
- Backups: `./backups/` (gitignored) — 2 dump'а после T3.4 smoke.
- **Alembic head: `b04677374b85`**. **Rule count: 24** (`config/rules/v1_uz_msb.yaml`). **KPI count: 8** (`ebitda`/`debt_to_ebitda`/`current_ratio`/`working_capital`/`interest_coverage`/`dscr`/`quick_ratio`/`fx_exposure_ratio` + legacy ROE/EBIT/etc).
- Deps Day 4: `networkx>=3.4` (graph cycle detection для CIRCULAR_INVOICING).

### Active focus — открытые направления (НЕ блокеры, dispatch по сигналу)

1. **T4 compliance pack**: skeleton доставлен (`docs/compliance/{admin-guide,security-architecture,drp-bcp}.md`, 1007 строк bilingual RU+UZ). Открыто: UZ-перевод (грепай `TODO[CA-T4-UZ]`) — нужен носитель / compliance-эксперт; pentest узб-лаборатории; аттестат УзСтандарта на ПДн (Закон РУз №547); IT-Park / Uzinfocom резидентство. Старт за 2 мес до bank tender.
2. **Real-bank pilot trip**: install playbook `deploy/README.md` + demo walkthrough `docs/demo/scenarios.md` (5 готовых сценариев на существующих BR-2026-00XX) + onboarding session с пилот-банком.
3. **Pre-pilot smoke (✋ обязательно перед demo trip)** — playbook `docs/operations/pre-demo-smoke.md`: 8 routes × 3 темы + 4 пути 2FA + 8 edge-UX сценариев (Блок 5). Console-error gate, sign-off table. Прогон ~60–90 минут, повторный за 24 часа до выезда.
4. **Post-demo hardening backlog** (не блокеры): CI Docker job · Sentry sourcemaps upload через release pipeline (`sentry-cli sourcemaps upload`) · AlertManager rules-as-code · **T2.1b** real-fixture smoke на «млн / полные сум» multiplier branches FORM_1/2 · **T2.4b** faktura.uz real client (pre-condition: пилот-банк OAuth-токен) · **T1.5b** OAuth2/OIDC AuthnAdapter (pre-condition: запрос Okta/Azure AD) · **T1.5c** openldap testcontainer.
5. **ADR-0024 backlog**: **CA-070** fx_exposure_ratio thresholds (verified § ЦБ РУз для FX-mismatch у МСБ) · **CA-002b** CIRCULAR external_invoices (cross-CP ESF source для 3+ node циклов) · **Tier 4 OKVED → ОКЭД catalog rename** (~12-15 файлов, `config/catalog/okved.json` → `oked.json`, frontend endpoint) · **OFF_BALANCE manual-input UI wiring** (3 поля в Pydantic + wizard Step 2) · **OKVED_CHANGED_12M brand-new dossier flow** (требует Госкомстат ОКЭД-API) · **OKVED_CHANGED_12M dual-severity** через `severity_override` · **SINGLE_BUYER_CONCENTRATION dual-severity** (0.50/0.70) · **LOW_MARGIN_HIGH_TURNOVER vs industry_median** (stat.uz net-margin catalog по ОКЭД).
6. **Active code-level TODOs** (`grep TODO\[CA- src/ web/src/`): **CA-001** ИНН checksum по ГНК-алгоритму · **CA-002b** CIRCULAR external invoices · **CA-003** Real ГНК lookup (pre-condition: legal review, см. также CA-DS28) · **CA-019** Access-token denylist для force-logout · **CA-031** Source-trail invasive refactor (`applyToForm` все ячейки формы) · **CA-DS19** Pulse-dot motion cleanup в DSCR-summary · **CA-DS25** KPI sparkline (pre-condition: monthly_turnover≥12 источник) · **CA-DS28** ГНК public lookup на soliq.uz/services/search/ (pre-condition: legal review).

### Frozen scope (не трогать до post-demo)

- UI polish: новые цвета, шрифты, тени, анимации.
- Расширения dark theme, 4-я тема, accent variants.
- Новые design tokens, brand-tenant новые секции.
- CA-DS25 (KPI sparkline) до monthly_turnover-источника (VAT_DECL monthly chain или ESF), новые OKVED-каталог расширения сверх baseline.
- i18n keys refactor, новые ADR по визуальному дизайну.
- Coverage сверх baseline ради числа — кроме тестов на новый Pre-Demo код.
- Refactor без бизнес-причины из roadmap.

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

1. **`npm ci` ≠ `npm install`**. После добавления зависимости — `rm -rf node_modules package-lock.json && npm install`, потом `npm ci` локально чтобы воспроизвести CI-режим.
2. **`ruff check` + `mypy --strict` + `pytest`** обязательны перед push. **`pytest src/ tests/` — оба обязательны** (`src/` co-located unit-тесты + `tests/` integration / e2e). Минимум: `docker compose exec -T api bash -c "cd /app && uv run python -m ruff check . && uv run python -m mypy --strict src tests && uv run python -m pytest"`. Memory `feedback_pytest_tests_dir_in_prepush.md` — пропуск `tests/` ловит на CI red push.
3. **Меняешь computed-from-X invariant — `grep -r` все тесты на эту semantic.** Локальный mapper-test может пропустить интеграционный тест.
4. **Меняешь rule registry / rule count** — `grep -rn "== <old_count>\|== <new_count>" tests/ src/` обязателен (Session 2 lesson: 4 hardcoded assertions проворонились, CI 3× красный до hotfix).
5. **CI коммита перед твоим зелёный?** `gh run list --branch main -L 3` перед началом работы.

---

## Architecture Reminders

- `domain/` не знает про `infrastructure/` — никогда.
- Все бизнес-правила — только в `domain/rules/`, ссылка на источник обязательна.
- Новый банк = новый adapter, не правки в ядре.
- Two modes (Bank / Accountant) — два UI поверх одного бизнес-ядра.

## Security Hard Rules

- Данные заёмщиков не логируются.
- Никаких внешних API в production (только on-premise).
- Soliq данные — только через официальный экспорт/API, не scraping (исключение — публичный лукап `soliq.uz/services/search/` после legal review, см. CA-DS28).
- `.env` не в git, secrets через Vault в production.

## Operations playbooks

- **Pre-demo smoke** (gate перед pilot trip, ~60–90 мин) — `docs/operations/pre-demo-smoke.md`.
- **Pre-demo smoke history** журнал — `docs/operations/pre-demo-smoke-history.md`.
- **Demo scenarios walkthrough** (5 готовых borrower'ов, ~25–30 мин) — `docs/demo/scenarios.md`.
- **2FA smoke** (4 пути, ~10 мин) — `docs/operations/2fa-smoke.md`.
- **PII key rotation + recovery** — `docs/operations/pii-key-rotation.md` (T1.3 / ADR-0017).
- **Multi-tenant deploy** (separate compose-project per bank) — `docs/operations/multi-tenant-deploy.md` (T1.4 / ADR-0018).
- **LDAP setup + ops runbook** — `docs/operations/ldap-setup.md` (T1.5 / ADR-0019).

---

## Start of Session Command

```
Прочитай @PROJECT_BRIEF.md целиком, потом @CLAUDE.md, затем ОБЯЗАТЕЛЬНО
@docs/conventions/active-contracts.md (живые domain/persistence/rules/UI
контракты — без него не сможешь корректно менять код).
Скажи на каком phase мы сейчас и какая следующая atomic задача.
Не начинай кодить — сначала покажи план.
```

Если нужна историческая глубина:

- `docs/session-log.md` — chronology по сессиям/дням с commit hashes + lessons
- `docs/conventions/active-contracts.md` — все CA-XXX, JSONB patterns, severity-override, KPI level_tone, frontend/PDF/i18n contracts
- `docs/design-sweep-archive.md` — детали Phase 1-10 (preview HTML, итерации, lessons) + final status snapshot
- `docs/operations/2fa-smoke.md` — пошаговая инструкция smoke 2FA
- `docs/adr/` — Architecture Decision Records (0001..0024)
- `docs/compliance/` — T4 артефакты (Admin Guide, Security Architecture, DRP/BCP) для bank tender pack
- `docs/research/2026-05-19-3way-reconcile/` — Claude / ChatGPT / Qwen research outputs за ADR-0024
