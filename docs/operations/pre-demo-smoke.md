# Pre-demo smoke (gate перед pilot trip)

> Обязательный live-browser walkthrough всей системы перед demo для пилот-банка.
> RTL / jsdom / vitest **не ловят** hydration mismatches, visual regressions, nested anchor warnings, missing i18n keys в `t.rich` (lesson `feedback_nested_anchor_rtl_blind`).
> Только реальный браузер. ~60–90 минут на полный прогон.

---

## Pre-flight

1. **CI main зелёный**:
   ```powershell
   gh run list --branch main -L 3
   ```
   Все три PASS. Если красный — стоп, сначала чинить.

2. **Stack up & healthy**:
   ```powershell
   docker compose ps
   ```
   Ожидаем: `credit-api` healthy, `credit-postgres` healthy, `credit-redis` healthy, `credit-db-backup` up.

3. **Backend env sanity**:
   ```powershell
   docker compose exec -T api bash -c 'env | grep -E "^(APP_MODE|BRAND_ID|PII_ENC_KEYS|REDIS_URL|AUTHN_MODE)="'
   ```
   Ожидаем: `APP_MODE=bank`, `BRAND_ID=default` (или `uzbekbank` для UZ-прогона), `PII_ENC_KEYS` задан, `REDIS_URL` задан.

4. **Seeded analyst**:
   ```
   email:    t04@bank.uz
   password: T04Smoke!
   2FA:      выкл (для основного прохода). Отдельно — Путь 2FA по docs/operations/2fa-smoke.md.
   ```

5. **Dossier для просмотра**: `BR-2026-0048` (последний smoke'нутый, см. CLAUDE.md Stack state).

6. **Frontend dev**:
   ```powershell
   cd web; $env:NEXT_PUBLIC_APP_MODE='bank'; $env:NEXT_PUBLIC_BRAND_ID='default'; npm run dev
   ```
   Дождаться `✓ Ready in Xs` без warnings.

7. **DevTools open** на каждом прогоне: вкладка **Console**, фильтр `Errors + Warnings`. Цель — 0 записей на каждом маршруте.

---

## Acceptance matrix — 8 routes × 3 темы

8 routes:

| # | Route | Smoke action | Что проверяем визуально |
|---|---|---|---|
| 1 | `/` | Открыть в чистой incognito-сессии | Редирект на `/login` (или `/search` если уже залогинен). Нет flash unstyled content. |
| 2 | `/login` | Submit `t04@bank.uz` / `T04Smoke!` | Inputs aligned, кнопка submit реактивна, после success → `/search`. |
| 3 | `/search` | Ввести ИНН несуществующий и существующий | Loading-state, empty-result UI, dossier-card открывается. |
| 4 | `/history` | Открыть с непустым списком | 48 dossiers, sticky-header, sort/filter chips. |
| 5 | `/dossier/BR-2026-0048` | Прокрутить все 7 разделов | A — identification, B — financials charts, C — turnover dynamics, D — counterparties, E — tax discipline, F — red flags, G — summary score. PDF-кнопка работает. |
| 6 | `/manual-input` | Пройти wizard Шаг 1 → 2 → 3 → Generate | Step navigation, source-trail badges (auto/auto-edited/manual), validation на required, финальный submit генерирует dossier и редиректит на `/dossier/{new_id}`. |
| 7 | `/help` | Развернуть все FAQ, проверить support tile | Phone/email/slack из brand-config, business-hours rendered, FAQ accordions. |
| 8 | `/settings` | Profile / Appearance / Security / About | Все 4 раздела. Theme-switcher работает (тест в Темах ниже). Change-password flow без ошибок. About → uptime calendar 30 дней. |

3 темы — переключение через `/settings → Внешний вид` или toggle в sidebar:

| Тема | Что проверяем |
|---|---|
| **light** | Контраст, читаемость, brand-primary в hover/active. PDF download — UZS-цвет, footer-цвет. |
| **dark** | Все семантик-tokens (--surface, --ink-*, --state-*) переключились. **PDF документ остаётся light forever** (CA-DS5). Charts читаются на тёмном. |
| **system** | Подвязка к `prefers-color-scheme`. Сменить OS-тему во время сессии — UI обновляется live через matchMedia listener (CA-DS5). |

**Acceptance**: 8 × 3 = **24/24 PASS**. Любая ячейка FAIL → задокументировать в Issues + fix перед demo.

### Console-error gate

На каждом из 24 проходов:

- Hydration mismatch (any "Hydration failed because…", "Text content did not match…") = FAIL.
- Nested anchor warning ("validateDOMNesting: <a> cannot be a descendant of <a>") = FAIL.
- next-intl missing key ("MISSING_MESSAGE: Could not resolve…") = FAIL.
- React error boundary tripped (red overlay в dev-mode) = FAIL.
- 4xx/5xx fetches в Network tab при штатном использовании = FAIL.

Allow:
- "Download the React DevTools…" (info).
- Fast Refresh logs (info).
- Vercel/Next telemetry pings.

---

## 2FA flows (4 пути, ~10 минут)

Делегировано в `docs/operations/2fa-smoke.md`. Прогнать **на текущей сборке** все 4 пути:

- Enrollment → Login через TOTP → Login через backup-код → Disable.

Acceptance: 4/4 пути PASS, backup-code сгорает после первого использования.

---

## Edge UX matrix (Блок 5)

Что user видит когда что-то ломается. Каждый сценарий — отдельный сеанс.

| # | Сценарий | Как воспроизвести | Acceptance |
|---|---|---|---|
| E1 | **API down** | `docker compose stop api`, обновить `/search` | Не whitescreen. Error-banner «Сервис недоступен» или skeleton + retry. После `docker compose start api` UI восстанавливается. |
| E2 | **API 500** | API guard: вернуть 500 на любой endpoint (можно вручную через curl POST на несуществующий путь и проверить error-handling в UI на реальном flow) | Тост / inline-error с понятным текстом, не stack-trace. Retry кнопка где применимо. |
| E3 | **Empty search** | `/search` → ИНН `999999999` (несуществующий) | Empty-state с подсказкой «Не найдено. Попробуйте создать вручную → /manual-input». |
| E4 | **Borrower без xltx** | Через `/manual-input` без upload xltx — только manual ввод во всех полях | Wizard проходит, dossier создаётся, в G-разделе risk-score есть, source-trail показывает manual везде. |
| E5 | **PDF gen latency** | `/dossier/{id}` → клик «Скачать PDF» | Loading-spinner, кнопка disabled во время gen, success → download trigger. Если >10s — не зависает, не повторяет click. |
| E6 | **Refresh-token revoked mid-session** | В Redis: `DEL refresh:denylist:<jti>` всех, или `FLUSHDB`. В UI триггернуть refresh (подождать 15м access-ttl или симулировать) | Redirect на `/login` с сохранением URL для return-after-login. Нет потери данных wizard если был в process (или явный warning «session expired, please save draft»). |
| E7 | **Network drop mid-wizard** | DevTools → Network → Offline → submit Шаг 3 | Toast «Нет сети», submit-кнопка не disabled навсегда, после restore retry работает. |
| E8 | **Slow API** | DevTools → Network → Slow 3G → `/dossier/{id}` | Skeleton placeholders, не whitescreen, charts ждут данные. |

Acceptance: **8/8 PASS** или каждый FAIL зарегистрирован как issue с severity (block/non-block для demo).

---

## Sign-off

Заполнить дату/инициалы после прогона. Без всех зелёных — на пилот не едем.

| Блок | Status | Дата | Кто |
|---|---|---|---|
| Pre-flight checks (1–7) | ☐ |  |  |
| Routes × Themes (24/24) | ☐ |  |  |
| 2FA пути (4/4) | ☐ |  |  |
| Edge UX (8/8) | ☐ |  |  |
| Issues registered | ☐ |  |  |
| Demo trip GO/NO-GO | ☐ |  |  |

---

## После прогона

1. **CLAUDE.md**: обновить «Stack state» датой последнего pre-demo smoke + ссылку на коммит этого playbook (или последний коммит фикса из этого прогона).
2. **Issues**: всё что FAIL — atomic tasks, fix → re-run только затронутый блок (не весь playbook).
3. **Демо-окно**: повторный полный прогон **за 24 часа до выезда** на пилот. Между прогонами — заморозка scope: только critical bugfix.
