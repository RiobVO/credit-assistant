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
| 4 | `/history` | Открыть с непустым списком | 52 dossiers, sticky-header, sort/filter chips. |
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

### Acceptance grid (per-cell tick)

Проставь `☑` после успешного прохода ячейки. Любая `☐` к моменту GO/NO-GO = блокер.

| Route                          | light | dark | system |
|--------------------------------|:-----:|:----:|:------:|
| `/`                            |  ☐   |  ☐   |   ☐   |
| `/login`                       |  ☐   |  ☐   |   ☐   |
| `/search`                      |  ☐   |  ☐   |   ☐   |
| `/history`                     |  ☐   |  ☐   |   ☐   |
| `/dossier/BR-2026-0048`        |  ☐   |  ☐   |   ☐   |
| `/manual-input` (Step 1→2→3)   |  ☐   |  ☐   |   ☐   |
| `/help`                        |  ☐   |  ☐   |   ☐   |
| `/settings`                    |  ☐   |  ☐   |   ☐   |

**Что специфично смотреть на пересечениях:**

- **light** — brand-primary в hover/active кнопках, контраст серого текста (`--ink-3`) на `--surface`, читаемость chart-labels на белом фоне. На `/dossier` — UZS-suffix и footer цвета в PDF preview.
- **dark** — контраст charts (Recharts палитра против `--surface-2`/`--surface-3` тёмного), переход `--state-bad-bg` на анфрахитном фоне (не сливается), border'ы карточек (`--ink-4` тёмный — не невидимый), source-trail border bar (CA-DS21: зелёный/синий/серый/amber — все читаются). `/dossier` PDF documentation **остаётся light forever** (CA-DS5) — проверь что download'нутый PDF не тёмный.
- **system** — после initial paint смени OS theme (Win11: Settings → Personalization → Colors → Mode) **во время сессии** — UI должен переключиться live через matchMedia listener (CA-DS5), без F5. SSR no-FOUC: hard refresh (Ctrl+F5) на каждом route в режиме system — нет flash светлой темы у dark-OS.

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

Полный playbook — `docs/operations/2fa-smoke.md`. Здесь — короткий re-statement 4 путей с expected outcome каждого. Прогнать **на текущей сборке**.

1. **Enable (Enrollment)** — `/settings → Безопасность → Включить 2FA` → scan QR в Authenticator → 6-значный код → скачать `.txt` с 10 backup-кодами.
   *Expected*: карточка 2FA зелёная «Активна», `.txt` содержит 10 строк × 8 символов (A-Z 0-9).
2. **Login через TOTP** — logout → `/login` email+пароль → step-2 → свежий 6-значный код.
   *Expected*: redirect на `/search`, audit-log `login` event содержит `mfa=totp`.
3. **Recovery (login через backup-код)** — logout → `/login` email+пароль → step-2 → ссылка «Использовать резервный код» → один из сохранённых.
   *Expected*: redirect на `/search`; повторный ввод того же кода даёт `invalid_code` (код сгорает).
4. **Disable** — `/settings → Безопасность → 2FA → Отключить` → пароль + свежий TOTP.
   *Expected*: карточка серая «Не настроена», `mfa_secret` и `mfa_backup_codes_hash` в БД = NULL.

**Negative-path inline check** (не отдельный путь, но обязательная micro-проверка на пути 2):

- Введи **неправильный** 6-значный код на login step-2 → expect `invalid_code` с понятным текстом ошибки, **не** stack trace; retry-counter не блокирует input навсегда; нет утечки access/refresh-token (DevTools → Network → нет `Set-Cookie ca_access` в response failed login).

Acceptance: **4/4 пути PASS** + negative-path не выдаёт токен. Backup-code сгорает после первого использования.

---

## Edge UX scenarios (Блок 5)

Что user видит когда что-то ломается. Каждый сценарий — отдельный сеанс. Все 8 — обязательны.

### E1 — API kill

**Repro**: `docker compose stop api`, в UI обновить `/search` (F5).

**Expected UI**: не whitescreen. Error-banner «Сервис недоступен» или skeleton + retry-кнопка. Sidebar / header не падают (рендерятся из cached app-shell). После `docker compose start api` + retry — UI восстанавливается, не требует full reload.

**Pass criteria**: ☐ нет whitescreen · ☐ retry работает после restart · ☐ console без unhandled promise rejection.

### E2 — API 500 / 504

**Repro**:
- 500: спровоцировать backend exception — например, POST на `/api/dossier` с заведомо невалидным JSON (`Content-Type: application/json` + body `{`).
- 504: throttling proxy / network conditioner (DevTools → Network → custom profile с latency 30s) на любой `/api/...` запрос — backend ответ дольше gateway timeout'а.

**Expected UI**: toast / inline-error с понятным русским текстом («Сервер вернул ошибку», «Сервис не отвечает» — не голый `500 Internal Server Error`). Retry-кнопка где применимо (`/search`, `/dossier` PDF download, manual-input submit). Stack-trace **не виден** пользователю.

**Pass criteria**: ☐ нет stack-trace · ☐ retry доступен · ☐ correlation_id видим в DevTools response headers (для T3.2 поддержки).

### E3 — Empty search

**Repro**: `/search` → ИНН `999999999` (несуществующий формат ОК, но нет в БД).

**Expected UI**: empty-state с illustration / иконкой + текст «Не найдено» + подсказка-CTA «Создать вручную → /manual-input». Кнопка-link на manual-input реактивна.

**Pass criteria**: ☐ empty-state читаемый · ☐ CTA ведёт на `/manual-input` · ☐ нет 404 baner / stack.

### E4 — Borrower без xltx

**Repro**: `/manual-input` → Step 1 заполнить руками без upload xltx → Step 2 руками все поля → Step 3 руками → Generate.

**Expected UI**: wizard проходит без ошибок «требуется upload»; dossier создаётся; в `/dossier/{new_id}` раздел G (summary) содержит risk-score; source-trail в Step 2 (если открыть draft заново) показывает `manual` на всех полях (без зелёного auto badge'а).

**Pass criteria**: ☐ wizard submit success · ☐ dossier открывается · ☐ source-trail = manual везде · ☐ red-flag engine отработал (или явный пустой список без падения).

### E5 — PDF gen latency (>10s)

**Repro**: `/dossier/{id}` → клик «Скачать PDF». Для гарантированного latency — выбрать dossier с большим набором evidence (например `BR-2026-0042`, имеет много counterparties).

**Expected UI**: loading-spinner на кнопке, кнопка `disabled` во время gen (нельзя кликнуть повторно — нет дубля jobs). Success → trigger native download. Если gen >10s — UI не зависает, не показывает «Сервер не отвечает», audit-log `download_pdf` фиксирует только один event.

**Pass criteria**: ☐ нет double-click race · ☐ spinner виден · ☐ download trigger срабатывает · ☐ audit-log один event per click.

### E6 — Refresh-token revoked mid-session

**Repro**: залогинен. В Redis: `docker compose exec -T redis redis-cli FLUSHDB` (стирает refresh denylist полностью) **или** заденилист'ить конкретный jti через CLI. В UI выждать 15 мин access-ttl ИЛИ симулировать через DevTools — Application → Cookies → удалить `ca_access` и триггернуть запрос к `/api/...`.

**Expected UI**: redirect на `/login` с query `?next=<original_path>` (return-after-login сохранён). Если был в wizard mid-flow — явный toast/banner «Сессия истекла, черновик сохранён» (draft persistence per CA-058 / TTL 30d). Нет потери данных при re-login → return на `/manual-input` → restore draft видим в Step 1 prefill.

**Pass criteria**: ☐ redirect с next= · ☐ draft не теряется · ☐ после re-login возврат на исходный route · ☐ нет infinite-loop refresh→401→refresh.

### E7 — Network drop mid-wizard

**Repro**: `/manual-input` Step 2 заполнить → DevTools → Network → Offline → submit Step 3 (Generate).

**Expected UI**: toast «Нет сети, проверьте подключение». Submit-кнопка возвращается в active (не disabled навсегда). После DevTools → Network → Online → повторный click submit-кнопки проходит, dossier создаётся.

**Pass criteria**: ☐ toast виден · ☐ кнопка не зависает в disabled · ☐ retry после restore сетки работает · ☐ нет дубля dossier'ов в БД (idempotency).

### E8 — Wizard partial submit & recovery

**Repro**: `/manual-input` Step 1 заполнить → Continue к Step 2 → заполнить половину полей → закрыть вкладку (или logout). Re-login. Открыть `/manual-input` или drafts list.

**Expected UI**: draft восстанавливается — prefill через sessionStorage (Step 1 borrower-карточка per CA-058) + drafts table (TTL 30d) для Step 2 финансов. Пользователь видит «Восстановить черновик от <дата>» и продолжает с Step 2 без потери данных. После полного submit (Step 3 → Generate) draft удаляется.

**Pass criteria**: ☐ draft жив после close/logout · ☐ TTL ≤30 дней соблюдается · ☐ после успешной генерации draft удаляется · ☐ нет дубль-drafts при повторных open/close циклах.

Acceptance: **8/8 PASS** или каждый FAIL зарегистрирован как issue в `pre-demo-smoke-history.md` с severity (block/non-block для demo).

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

### Detailed per-cell log

Шаблон для построчного журналирования прохода. Заполнять в режиме «одна ячейка matrix / один edge-сценарий / один 2FA путь = одна строка». Полный лог прогона дублируется в `pre-demo-smoke-history.md` как отдельная запись.

| Дата | Route | Theme | Status (PASS/FAIL) | Notes | Signed by |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

---

## После прогона

1. **CLAUDE.md**: обновить «Stack state» датой последнего pre-demo smoke + ссылку на коммит этого playbook (или последний коммит фикса из этого прогона).
2. **`pre-demo-smoke-history.md`**: добавить запись о прогоне (формат — header `### YYYY-MM-DD — <инициалы>`, baseline commit, results, issues found, sign-off). См. `docs/operations/pre-demo-smoke-history.md`.
3. **Issues**: всё что FAIL — atomic tasks, fix → re-run только затронутый блок (не весь playbook).
4. **Демо-окно**: повторный полный прогон **за 24 часа до выезда** на пилот. Между прогонами — заморозка scope: только critical bugfix.
