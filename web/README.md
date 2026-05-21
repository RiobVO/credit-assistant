# web/ — credit-assistant frontend

Next.js 16 (App Router) фронт под две инсталляции одного бизнес-ядра:
**Bank Mode** (`(bank)` route group — `/login`, `/search`, `/history`,
`/dossier/[id]`) и **Accountant Mode** (`(accountant)` route group —
`/manual-input` wizard). Какие маршруты доступны, определяет
`NEXT_PUBLIC_APP_MODE` + flow в `src/app/layout.tsx`.

## Quick start (local dev)

```bash
npm ci
cp .env.local.example .env.local
# поправь NEXT_PUBLIC_API_URL, NEXT_PUBLIC_BRAND_ID, NEXT_PUBLIC_APP_MODE
npm run dev
```

Dev-сервер поднимется на `http://localhost:3000`. Backend ожидается на
`NEXT_PUBLIC_API_URL` (по умолчанию `http://localhost:8000` —
compose-сервис `credit-api`).

## Production build

```bash
npm run build
npm run start
```

Docker-образ — `web/Dockerfile` (multi-stage, Next standalone output).
Сборка в compose: `docker compose up -d --build web`.

## Env vars

См. `.env.local.example`. Минимум для запуска:

| Var | Назначение |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend FastAPI URL (compose: `http://localhost:8000`). |
| `NEXT_PUBLIC_APP_MODE` | `bank` или `accountant` — определяет какой route group рендерится. |
| `NEXT_PUBLIC_BRAND_ID` | Brand-tenant ID (`default` / `uzbekbank` / ...). Резолвится в `config/brands/<id>.json` на backend. |
| `NEXT_PUBLIC_LOCALE` | Install-default локаль (`ru` / `uz`). Runtime switch — через `ca_locale` cookie. |
| `NEXT_PUBLIC_SENTRY_DSN` | Опционально, для production telemetry. |

## Tests

```bash
npm test        # vitest watch
npm run test:run # one-shot для CI
```

Стек: `vitest` + `@testing-library/react` + `jsdom`.
**Каждый test-файл с `fireEvent`/`click`** обязан вызывать
`afterEach(cleanup)` — auto-cleanup `testing-library` не покрывает full
vitest-run и ломает соседние файлы DOM-leak'ом
(memory `feedback_vitest_dom_leak_cleanup.md`).

## Brand-tenant

`src/lib/brand-context.tsx` экспортит `useBrand()` — hook с
brand-specific UI данными (support email/phone, business hours,
default locale, theme tokens). Загружается на server-side из
`/api/brand-config` и пробрасывается через React context. Новый банк
= новый `config/brands/<id>.json` на backend, никаких правок здесь.

## i18n

`next-intl` 4.11. Ключи — `src/i18n/{ru,uz}.json`. Конфиг
`src/i18n/request.ts`. Runtime locale switcher (`src/components/locale-switcher.tsx`)
пишет `ca_locale` cookie через server action `setLocaleAction`
(`src/app/_actions/set-locale.ts`); install-default берётся из
`NEXT_PUBLIC_LOCALE` env. Fallback chain — cookie → env → `"ru"`
(см. `src/lib/locale-cookie.ts`).

## Связанные документы

- `../CLAUDE.md` — общий project context + runtime state.
- `../docs/conventions/active-contracts.md` — frontend contracts (CA-053+, CA-DS series, JSONB-payload patterns).
- `../docs/adr/` — Architecture Decision Records (0001..0024, в т.ч. CA-DS design-sweep).
- `../docs/audit/2026-05-21/00-summary.md` — independent audit findings (5 areas, priority-ranked).
- `../docs/operations/pre-demo-smoke.md` — live-browser smoke playbook перед pilot trip.
