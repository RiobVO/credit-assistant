# Demo readiness audit — credit-assistant 2026-05-21

## Executive summary

Демо в текущем состоянии **выполнимо на нашем хосте** (5 целевых dossiers
существуют, PDF рендерит за 0.75s, авторизация работает), но **не
воспроизводимо у пилот-банка через `deploy/install.sh`**: демо-данные
(`BR-2026-0030/0040/0042/0046/0047`) живут только в gitignored
`backup-pre-t13.sql`, а `scripts/seed_demo_borrowers.py` создаёт 3
других ИНН без гарантии конкретных case_id. Свежий инженер получит
пустой `/history`, и проводить demo будет некому.

Свежий инженер с README за 30 минут backend поднимет (Quick start
читаем), но live demo-walkthrough без manual `psql \copy` из dump'а не
получится. Кроме того, banker увидит ряд polish-багов: «Accountant Mode»
tagline в bank-UI с `BRAND_ID=default`, mock «verified» badge на ИНН в
manual-input wizard, имена аналитиков «T0.4 Smoke» и «T1.1 Smoke Tester»
в списке /history, борроверы «TEST» / «ЙЦУЙЦУЙЦУ» / «OOO Test T1.1»
рядом с серьёзными ООО.

## Demo readiness score: 5/10

- +2 stack стабильный, healthcheck'и зелёные, PDF быстрый, list-history
  одной JOIN-выборкой (10 ms на 24 строки).
- +1 5 сценариев dossiers найдены в БД, scoring + red_flags соответствуют
  narrative `docs/demo/scenarios.md`.
- +1 i18n покрытие симметричное (`ru.json` и `uz.json` по 867 строк),
  без TODO в i18n.
- +1 install.sh + .env.example существуют и валидируют обязательные
  секреты (JWT_SECRET, PII_ENC_KEYS, BRAND_ID).
- −2 demo data в gitignored SQL-dump, не репродуцируется через
  `seed_demo_borrowers.py`; install.sh seed'ит только админа.
- −1 mock «verified» badge на ИНН в wizard ничем не отличим от реального
  ГНК lookup'а — это decision-screen mock (см.
  `feedback_mock_ui_on_decision_screens.md`).
- −1 `BRAND_ID=default` brand-tagline = "Accountant Mode" — отображается
  в bank-mode topbar и sidebar.
- −1 `/history` showcase загажен тестовыми борроверами и аналитиками с
  именами «T0.4 Smoke», «Smoke Тестер», «TEST», «ЙЦУЙЦУЙЦУ».

## Blockers (demo wouldn't work)

- **Demo dossiers не репродуцируются у пилот-банка.** Сценарии
  `BR-2026-0030/0040/0042/0046/0047` (`docs/demo/scenarios.md:32-119`)
  существуют только в gitignored `backup-pre-t13.sql` (`.gitignore:
  backup-pre-t13.sql`, `backups/`). `scripts/seed_demo_borrowers.py:79-128`
  создаёт 3 других ИНН (`301234567`, `402345678`, `503456789`) с
  Зумрад-Текстиль / Хосилот-Агро / ТехноСервис — но **NB** ни одного из
  целевых BR-2026-XX case_id seed не гарантирует: case_id выдаёт
  `SqlAlchemyCaseIdAllocator` из БД-sequence
  (`scripts/seed_demo_borrowers.py:275-279`), на пустой БД получится
  `BR-YYYY-0001`/`0002`/`0003`, а не `0030`/`0040`/`0042`. Tests
  (`tests/scripts/seed_demo_borrowers_test.py:19-21`) подтверждают
  «3 borrowers», а не 5 dossier'ов из demo scenarios.
- **install.sh не сидит demo-borrower'ов вообще.** `deploy/install.sh`
  поднимает stack и предлагает seed одного аналитика
  (`deploy/install.sh:167-170`), про demo dossiers — тишина.
  `deploy/README.md` ссылается на `docs/demo/scenarios.md`
  (`deploy/README.md:241`), но связи между installer и seed-script нет.

## Major friction (demo would feel rough)

- **`BRAND_ID=default` в bank-mode даёт wrong tagline.**
  `config/brands/default.json:4` → `"tagline": "Accountant Mode"`.
  Bank-mode topbar (`web/src/app/(bank)/_components/topbar.tsx:38`) и
  sidebar (`web/src/app/(bank)/_components/sidebar.tsx:97`) рендерят
  `brand.tagline`. CLAUDE.md Stack state указывает `BRAND_ID=default` как
  runtime значение — banker увидит «Credit Assistant · Accountant Mode»
  на каждой странице. (Текущий backend сейчас фактически `BRAND_ID=
  uzbekbank` per `docker compose exec api env`, но `docker-compose.yml`
  default — `default`).
- **Bank-history showcase загажен test-data.** На `/history`
  (`/api/bank/dossiers`) видны 24 dossier'а с такими borrower-именами:
  ```
   ЙЦУЙЦУЙЦУ              | 5  ← keyboard mash
   OOO Test T1.1          | 2  ← internal test
   TEST                   | 1  ← internal test
   кадр дон нон           | 13 ← опечатка, но реалистично
   ООО «Зумрад-Текстиль»  | 1
   ФХ «Хосилот-Агро»      | 1
   ООО «ТехноСервис Плюс» | 1
  ```
  + analyst names `T0.4 Smoke`, `T1.1 Smoke Tester`, `Smoke Тестер`
  показываются в колонке «Аналитик». Pre-demo smoke `docs/operations/
  pre-demo-smoke.md:56-58` пишет про 48 dossiers — у нас 52 в БД и 24 в
  bank-list. Drift.
- **Mock ГНК «verified» badge на ИНН в manual-input wizard.**
  `web/src/features/manual-input/components/step-1-borrower.tsx:354-359`
  — на любой 9-digit ИНН после `CHECK_DELAY_MS` ставится `verified`
  state c `summaryKey: "s1_inn_summary_mock"` →
  `web/src/i18n/ru.json:538` → «Юр. лицо · действующий статус». Banker
  поверит что есть live-проверка ГНК. Memory
  `feedback_mock_ui_on_decision_screens.md` уже подсветило этот класс
  проблем для UI принимающего решение. TODO[CA-003] в коде
  (`step-1-borrower.tsx:356`) подтверждает что это mock, но в UI это не
  отличить от реальности.
- **Demo dossiers stale при `rules_evaluated=19`, реальный YAML — 24
  правила.** `config/rules/v1_uz_msb.yaml` содержит 24 rule-id (grep
  `^  - id:`), но BR-2026-0030/0040/0042/0046/0047 в БД фиксируют
  `rules_evaluated: 19` (запрос выше). Это значит при пересоздании
  dossier'а у пилот-банка new-engine может выдать другой score (новые
  правила в YAML, не учтённые в snapshot'е). Demo «один borrower три
  снимка» (Scenario 3/4/5) потенциально не consistent с свежим engine.

## Polish issues (banker would notice)

- **2026-05-16 пропущен в uptime-history.** `GET /api/system/health/
  history` возвращает дни 13,14,15,17,18,19,20 — день 16 отсутствует
  (запись 8 из 8 в массиве `days`). На `/settings → О приложении`
  banker увидит дыру в календаре «доступности».
- **Brand support email inconsistency.** `/settings → About` рендерит
  i18n key `support_email` =`ops@uzbekbank.uz` (захардкожен в
  `ru.json:208`), а `/help` берёт из
  `brand.support.email` (`config/brands/default.json:14` →
  `support@credit-assistant.uz`). При `BRAND_ID=default` две страницы
  покажут разные emails.
- **PDF filename не human-readable.** `src/interfaces/api/shared/
  dossier_pdf.py:140-143` — `BR-{uuid.hex[:4]}.pdf` (например
  `BR-EDFD.pdf`), не `BR-2026-0046.pdf` который banker узнаёт из UI.
  Confusing trail в downloads/email.
- **`docs/operations/2fa-smoke.md:14-16` использует `admin@bank.uz`/
  `Admin2026!`, а `docs/operations/pre-demo-smoke.md:30-34` — `t04@bank.uz`/
  `T04Smoke!`.** Два разных seed-аналитика конвенции в operations docs.
  Презентёр должен помнить какой playbook где.
- **`web/.env.local.example` (`web/.env.local.example`) не содержит
  `NEXT_PUBLIC_BRAND_ID`.** Свежий разработчик скопирует example, не
  выставит brand, получит default → «Accountant Mode» tagline в
  bank-UI.
- **Login-view recovery link заглушка.** `web/src/app/login/_components/
  login-view.tsx:222` — TODO «реализовать восстановление через
  /api/auth/recover». Если banker кликнет «Забыли пароль» — ничего не
  произойдёт.
- **History filter — client-side only.** `web/src/app/(bank)/history/
  _components/history-view.tsx:140` — «Filtering recommendation + period
  — пока client-side (TODO: backend)». Banker фильтрующий «по периоду»
  на странице с pagination получит inconsistent UX (фильтр только в
  current page).
- **`/history` показывает 24 dossiers, pre-demo-smoke предполагает 48.**
  Расхождение в playbook — `docs/operations/pre-demo-smoke.md:57`
  «48 dossiers, sticky-header, sort/filter chips». При прогоне smoke
  оператор увидит другое число и подумает что что-то сломано.
- **`docs/demo/scenarios.md:37` ссылается на «19 правил отработали»** —
  но `config/rules/v1_uz_msb.yaml` теперь 24. Текст narrative устарел
  относительно ADR-0024 Day 4.

## Performance benchmark table

| Route | Estimate | Concern |
|---|---|---|
| `GET /api/bank/dossiers?page=1&page_size=20` | 10 ms / 6.3 KB, 2 SQL (count + items JOIN) | OK — single JOIN, no N+1. (`src/infrastructure/persistence/repositories/dossier_repository.py:199-235`) |
| `GET /api/dossier/{id}` | not measured (read-only audit) | LoadDossierForView через `storage.dossier`, прямое чтение по UUID + snapshot. |
| `GET /api/dossier/{id}/pdf?lang=ru` | **0.75 s** / 64 KB на `BR-2026-0046` (8 chunks PDF) | OK для demo `<10s` бюджета. WeasyPrint в `asyncio.to_thread` (`src/application/use_cases/render_dossier_pdf.py:85`), не блокирует event loop. **Synchronous per request** — нет background job; при concurrent download'ах thread-pool станет узким горлом. Singleton renderer через `@lru_cache` (`src/interfaces/api/shared/dossier_pdf.py:47-50`) экономит Jinja env init. |
| `/manual-input` wizard step transitions | client-side `useState` (`web/src/features/manual-input/manual-input-view.tsx:90`) | OK — instant, debounced readiness checks (`checklist.tsx:86`). |
| `POST /api/manual-input` (Generate) | not benchmarked | Включает: registry.run_all() + scoring + snapshot save + dossier save + case_id allocate. Под одной транзакцией. Без замера не оценить, но архитектурно ОК. |
| `GET /api/system/health/history` | 10 ms / 285 B | OK — pre-aggregated daily roll-up. |

## Scenario verification

| Dossier | Exists? | Status | Scenario claim plausible? |
|---|---|---|---|
| BR-2026-0030 | YES | score 6, approve, 2 flags | YES — DIRECTOR_CHANGED_6M (20 дней) + LOW_MARGIN_HIGH_TURNOVER (2.2% / 7.28 млрд) совпадают с `scenarios.md:76-82`. Borrower name «кадр дон нон» (ИНН 201308534) совпадает с narrative. |
| BR-2026-0040 | YES | score 0, approve, 0 flags | YES — clean dossier, `rules_evaluated: 19`. Зумрад-Текстиль narrative (`scenarios.md:32-50`) совпадает. **NB**: scenarios.md:37 пишет «все 19 правил», но в YAML сейчас 24 — текст устарел. |
| BR-2026-0042 | YES | score 0, approve, 0 flags | YES — Хосилот-Агро, scenarios.md:55-67 совпадает. |
| BR-2026-0046 | YES | score 21, review, 3 flags | YES — VAT_ESF_MISMATCH critical (diff 23%, period 2026-03) + DIRECTOR_CHANGED_6M (65 дней) + LOW_MARGIN_HIGH_TURNOVER — всё совпадает с scenarios.md:99-106. |
| BR-2026-0047 | YES | score 50, review, 4 flags | YES — VAT_ESF_MISMATCH + LOAN_TO_REVENUE_RATIO (loan 555.5 млрд, ratio infinity) + INSUFFICIENT_DATA + DIRECTOR_CHANGED_6M — совпадает с scenarios.md:124-131. **NB**: scenarios.md:121 пишет «Запрашиваем 555.5 млрд» а в evidence — `555555555555` сум (555.5 млрд). OK. |

## What works well

- **Полный E2E demo flow на нашем хосте работает.** PDF за 0.75 s,
  list за 10 ms, dossier scoring совпадает с narrative.
- **Идемпотентность compose stack:** все 4 контейнера healthy,
  `credit-db-backup` sidecar активен (T3.4 backup).
- **PII at rest шифрование живое.** `borrowers.name` colsum
  показал ciphertext `gAAAAABqCu...` для seed-borrower'ов — Fernet
  работает. Без PII_ENC_KEYS restore из dump не пройдёт (по design).
- **i18n паритет.** `ru.json` и `uz.json` одинаковой длины (867 строк
  каждый), без TODO в i18n, mock-ключи (`s1_inn_summary_mock`)
  переведены на оба языка.
- **Brand-config резолвится через ADR-0011/0018.** Frontend
  `web/src/lib/config.ts:17-19` авто-derive'ит `BRAND_ID` из
  `APP_MODE` (bank → uzbekbank), spec'ан тестами.
- **Console-error gate чистый.** Только 2 `console.error` в
  `app/(accountant)/error.tsx:17` и `app/(bank)/error.tsx:17` (error
  boundaries) — приемлемо.
- **`localhost:8000` — единственная захардкоженная константа** (один
  fallback в `web/src/lib/config.ts:2`), всё прочее env-driven.
- **WeasyPrint rendering в `asyncio.to_thread`** — event loop не
  блокируется на PDF gen.
- **List endpoint без N+1.** Single JOIN, count + items
  (`dossier_repository.py:199-235`).
- **Seeded analyst T0.4 работает**, login flow проходит за один POST
  на `/api/bank/auth/login`.

## Areas not verified

- **Live-browser smoke не прогнан** (нет browser tooling в этой сессии).
  Hydration mismatches, nested-anchor warnings (memory
  `feedback_nested_anchor_rtl_blind.md`) могли остаться. Pre-demo-smoke
  playbook `docs/operations/pre-demo-smoke.md` существует и охватывает
  8 routes × 3 темы, но самого прогона нет в истории
  (`docs/operations/pre-demo-smoke-history.md` не проверен).
- **PDF visual quality** не оценён — содержимое 64 KB бинарника не
  смотрел в виде картинки. `smoke-pdfs/` содержит 5 PDF файлов
  (ru.pdf, ru-bank.pdf, uz.pdf, uz-bank.pdf, nolang.pdf по 61-65 KB),
  но без preview tooling не могу подтвердить cyrillic+latin glyph
  coverage, layout, бренд.
- **Wizard E2E** (manual-input Step 1 → 2 → 3 → Generate) не прогонял —
  верифицировал только что step transitions client-side.
- **`POST /api/manual-input` latency** не замерял; в production будет
  под analyst-load — нужно реальное profiling если concurrent users >5.
- **Background jobs** для PDF generation отсутствуют — нагрузочный тест
  N concurrent PDF download'ов даст thread-pool saturation. Не блокер
  для demo, но pilot risk.
- **`docs/operations/pre-demo-smoke-history.md`** — журнал прогонов
  smoke — содержимое не прочитано. Если последний прогон давний или
  red, demo рискованный.
- **2FA flow** (`docs/operations/2fa-smoke.md`) на текущей сборке не
  прогонял — только проверил что endpoints `/api/bank/auth/mfa/*`
  существуют в OpenAPI.
- **Frontend `npm run build` не проверил.** Если production build падает
  на новых .tsx файлах — `/dossier`, `/history` отдадут 500.
