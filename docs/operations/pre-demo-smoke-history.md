# Pre-demo smoke — журнал прогонов

> Append-only лог каждого pre-demo smoke прогона перед pilot trip.
> Один прогон = одна `###` запись. Не редактировать старые записи —
> добавлять follow-up'ы новой записью.
> Playbook: `docs/operations/pre-demo-smoke.md`.

---

## Формат записи

Каждый прогон фиксируется отдельной секцией `### YYYY-MM-DD — <инициалы>` со следующими подразделами:

- **Baseline commit** — `git rev-parse HEAD` на момент старта прогона (важно: фиксирует точный slice кода, который смотрели).
- **Results** — итоги по блокам (pre-flight / routes×themes / 2FA / edge UX) с числовыми score'ами и checkbox'ами.
- **Issues found** — список найденных проблем с severity `block` (нельзя ехать на пилот) или `non-block` (поедем, fix в backlog). Owner + commit фикса заполняется по факту.
- **Sign-off** — финальный вердикт `GO` / `NO-GO` + дата подписи + инициалы подписанта.

Каждый прогон **дублирует** sign-off-таблицу из playbook'а, чтобы файл оставался самостоятельным артефактом аудита.

---

## Прогоны

### YYYY-MM-DD — <инициалы>

**Baseline commit**: `<sha>` (branch `<name>`)

**Окружение**:
- `APP_MODE`: bank / accountant
- `BRAND_ID`: default / uzbekbank
- Backend: `credit-api` healthy / degraded
- Frontend: `npm run dev` / production tarball

**Results**:

- Pre-flight checks (1–7): ☐
- Routes × Themes (24/24): _ / 24 — ☐
- 2FA пути (4/4): _ / 4 — ☐
- Edge UX (8/8): _ / 8 — ☐
- Console-error gate (0 errors / 0 warnings на каждом из 24 проходов): ☐

**Issues found**:

- [ ] `<E#>` / `<route×theme>` — `<краткое описание>`. Severity: block / non-block. Owner: `<инициалы>`. Fix commit: `<sha>` (заполняется после фикса).

**Sign-off**: GO / NO-GO — `<дата>` — `<инициалы>`

**Follow-up прогон** (если был NO-GO): ссылка на следующую запись с датой повторного прохода.

---

<!-- Новые записи добавлять выше этой линии, чтобы последний прогон был сверху. -->
