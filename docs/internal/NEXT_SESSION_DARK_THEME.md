# Prompt для следующей сессии — Dark theme + 3-theme switcher

> Скопируй блок ниже целиком в начало новой сессии. Контекст полный, исследование можно не повторять.

---

## TL;DR
Реализовать переключение тем `light` / `dark` / `system` в `/settings → Внешний вид`. Инфра наполовину готова (state в localStorage, `<html data-theme>` прокидывается). Не хватает: dark CSS-палитры, no-FOUC SSR-скрипта, разблокировки UI, аудита hardcoded colors. PDF досье — light forever.

## Принятые решения (Phase 0 закрыт)
- **Палитра**: slate/anthracite — surface `#0f1419`, ink `#e8edf5`. Banking-grade, GitHub/Linear vibe.
- **PDF lock**: остаётся light всегда. Зафиксировать в новом ADR-0013.
- **System mode**: live через `window.matchMedia('(prefers-color-scheme: dark)')` listener, не snapshot.

## Текущее состояние (что уже есть)
- `web/src/features/settings/use-appearance.ts` — state `theme: "light" | "dark" | "system"`, persist в localStorage `ca:settings:theme`, проставляет `<html data-theme>`. Но в UI dark/system **disabled** (см. комментарий line 68-70).
- `web/src/features/settings/appearance-section.tsx` — `ThemeSwatches` рендерит 3 кнопки.
- `web/src/app/globals.css:89` — `:root {}` блок с ~32 light-токенами. `[data-theme="dark"]` блока **нет**.
- `:root[data-brand="uzbekbank"]` (line 177) — brand-tenant override на brand-цвета.
- ~104 находки hardcoded `bg-white` / `text-black` / `#XXX` в `web/src/**/*.{tsx,ts}` (grep уже считал).

## Декомпозиция (8 фаз)

### Phase 1 · Dark palette в `globals.css`
- Новый блок `[data-theme="dark"]` после `:root {}` — переопределение всех ~32 семантик-токенов:
  - `--surface` `#0f1419`, `--surface-2` `#161b22`, `--surface-3` `#1e242d`, `--bg` `#0a0d12`
  - `--ink-1` `#e8edf5`, `--ink-2` `#c4cbd8`, `--ink-3` `#8a93a3`, `--ink-4` `#5e6675`
  - `--border` `#262d38`, `--border-strong` `#363f4d`
  - `--nav-*` тёмные оттенки сидбара
  - `--state-{ok,warn,bad,info,neutral}-{fg,bg,border}` — adjusted для dark (fg ярче, bg темнее, border контрастнее)
  - `--brand-primary-soft` `#3a2519` (10-15% brand-primary поверх dark surface)
  - `--brand-primary-ring` — opacity 0.35 вместо 0.2
  - `--chart-1..5` — насыщеннее для dark
- `@media (prefers-color-scheme: dark)` обёртка для `[data-theme="system"]` — переопределить под dark, иначе light при `prefers: light`.
- Контраст проверить WCAG AA: text ≥4.5:1, large text/UI ≥3:1. Спот-чек через DevTools eye-dropper.

### Phase 2 · SSR no-FOUC inline script
Без него reload даёт white→dark flash. В `web/src/app/layout.tsx` в `<head>` перед `<body>` вставить inline blocking script через `<script dangerouslySetInnerHTML>`:
```js
(()=>{try{const t=localStorage.getItem('ca:settings:theme')||'light';
const dark=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme:dark)').matches);
document.documentElement.dataset.theme=dark?'dark':'light'}catch{}})()
```
Script запускается синхронно до hydration → React monтuruется уже с правильным data-theme. После hydration `useAppearance` берёт верх.

### Phase 3 · Включить Dark + System в UI
- `appearance-section.tsx` — убрать `disabled` атрибут с dark/system swatches.
- `use-appearance.ts` — добавить `useEffect` с `matchMedia('(prefers-color-scheme: dark)')` listener для live system-mode sync; cleanup на unmount.
- Удалить устаревший комментарий «v1 только light selectable» в `applyToDocument` (line 68-70).

### Phase 4 · Audit hardcoded colors (~104 hits)
- `grep -rEn 'bg-white|text-white|bg-black|text-black|#[0-9a-fA-F]{6}' web/src/`
- Заменить на semantic tokens: `bg-white` → `bg-[var(--surface)]`, hex literals → ближайший token.
- ESLint `no-restricted-syntax` guard расширить с `src/features/**` + `src/components/**` на `src/app/**` (см. CA-062).
- Inline `style={{ background: "#fff" }}` — отдельно, ESLint не ловит.

### Phase 5 · Charts theme-aware (UI only)
- Dossier KPI sparklines + revenue chart в `/dossier`. Если используют recharts — пробросить `var(--chart-1)` через style.
- Frontend chart колоры определить под dark в Phase 1.
- PDF matplotlib chart `chart_renderer.py` — **не трогать**, остаётся light (CA-DS5/ADR-0013).

### Phase 6 · Tests
- Unit `web/src/features/settings/use-appearance.test.ts`: 3 theme toggle + LS persist + applyToDocument проставляет атрибут + matchMedia listener subscribe/unsubscribe.
- RTL `web/src/features/settings/appearance-section.test.tsx`: 3 swatch-кнопки активные, click меняет state + data-theme на root.
- **Live-browser smoke** (lesson из nested-anchor): пройти лично `/`, `/search`, `/history`, `/dossier/{id}`, `/help`, `/settings` × 3 темы. RTL/jsdom не ловят visual regressions; console + visual check.

### Phase 7 · ADR-0013
- `docs/adr/0013-three-themes-pdf-light-only.md`
- Context (banking pilot users + glare fatigue + WCAG)
- Decision (3 темы web + PDF locked light)
- Rationale: PDF = audit print artifact, dark print жрёт тонер, аудиторы привыкли к light layout.

### Phase 8 · Verify (pre-push checklist)
```bash
# Backend (no changes expected, sanity)
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"
# Frontend
cd web && npm run lint && npx tsc --noEmit && npx vitest run && npm run build
```
Plus live smoke per Phase 6.

## Файлы которые трону
- `web/src/app/globals.css` — Phase 1 (большой patch)
- `web/src/app/layout.tsx` — Phase 2 (5 строк)
- `web/src/features/settings/use-appearance.ts` — Phase 3 (matchMedia listener, удалить блокер)
- `web/src/features/settings/appearance-section.tsx` — Phase 3 (enable swatches)
- ~15-25 файлов в `web/src/**` — Phase 4 (audit replace)
- 2-3 chart-компонента в `web/src/features/dossier/**` — Phase 5
- `web/src/features/settings/use-appearance.test.ts` — Phase 6 (new)
- `web/src/features/settings/appearance-section.test.tsx` — Phase 6 (new)
- `docs/adr/0013-three-themes-pdf-light-only.md` — Phase 7 (new)
- `eslint.config.js` / `.eslintrc` — Phase 4 (расширить hex-guard)

## Открытые ссылки
- Существующий ADR-0011 — design tokens
- CA-DS5 — open TODO «dark theme» (этот task закроем)
- CA-062 — ESLint hex guard (расширим)

## Контекст ground truth
- Текущая ветка `main`, последний коммит — см. `git log -1`
- `APP_MODE=bank` в Docker (если изменилось — `APP_MODE=bank docker compose up -d --no-deps api`)
- `BRAND_ID=default` (uzbekbank доступен в `config/brands/uzbekbank.json`)
- Login dev: `admin@bank.uz` / `admin123` (role=analyst), `senior@bank.uz` / `senior123` (role=senior_analyst)

---

**Старт следующей сессии**: 
> Прочитай `docs/internal/NEXT_SESSION_DARK_THEME.md` целиком, потом @CLAUDE.md. Все решения приняты, контекст полный. Покажи план для Phase 1 (dark palette concrete hex-values по semantic-токенам) — потом стартуй.
