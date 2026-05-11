# ADR 0013: 3 темы интерфейса (light/dark/system) — PDF light forever

- **Status**: Accepted
- **Date**: 2026-05-16
- **Phase**: post-Design Sweep
- **CA-DS5** (closes), CA-062 (extends)

## Context

Design Sweep (Phase 1-10) закрыт в `light` теме — banking aesthetic
(slate/anthracite ink + cream/navy сайдбары), credit memorandum PDF. UX-feedback
из пилотного банка после первых недель dogfooding'а:

- **Glare fatigue**. Аналитики проводят 6-8 часов в день в инструменте,
  light-only при работе в open-space с lateral windows вызывает eye strain
  к 16:00. Запрос «можно тёмную тему» прозвучал в 3 из 5 интервью.
- **Compliance officer use-case**. Compliance проверяет дossier поздно вечером
  (часто после рабочего дня) — light theme на затемнённом мониторе мешает
  фокусу на красных флагах.
- **WCAG AA**. Текущая light-палитра проходит AA, но `ink-3` на `surface-2`
  балансирует на грани 4.5:1. Dark theme с правильной палитрой даёт
  больший headroom (~9-12:1 для `ink-2`/`surface`).
- **OS preference**. macOS Sonoma и Windows 11 защищают user choice через
  system-wide setting. Игнорировать его в финансовом инструменте, который
  стоит на дашборде весь день — fashion-неприемлемо в 2026.

Infrastructure уже наполовину готова: `useAppearance` (Phase 5 Settings) хранит
`theme: "light" | "dark" | "system"` в localStorage, проставляет
`<html data-theme>`. Не хватало dark CSS-палитры, SSR no-FOUC скрипта и
matchMedia listener'а для live system-mode.

PDF досье — отдельный artefact. Аудиторы CB РУз и compliance смотрят
напечатанные / экранно-белые PDF годами. Темная печать жрёт тонер,
contrast-checker в audit-tooling рассчитан на light-on-white. Делать
PDF тёмной версии = breaking change для compliance workflow без upside'а.

## Decision

**3 темы в web-интерфейсе**:

1. `light` — текущий Design Sweep look, single tenant default.
2. `dark` — slate/anthracite (`#0A0D12` background, `#0F1419` surface,
   `#E8EDF5` ink-1). Banking-grade, Linear/Vercel pattern. Brand-primary
   (`#1E55C9` для default tenant) остаётся **константой** в обеих темах —
   tenant identity не размывается. Soft / ring / ink производные адаптируются.
3. `system` — следует за `prefers-color-scheme` через `matchMedia`. Live
   sync через `addEventListener('change')` в `useAppearance` hook.

**PDF досье — light forever**. WeasyPrint templates остаются на текущей
light-палитре независимо от user theme preference. Endpoint
`GET /api/dossier/{id}/pdf` игнорит `data-theme` cookie / header.

**uzbekbank brand-tenant в dark mode**: warm-cream sidebar (Brunello
Cucinelli aesthetic, light-only) **не воспроизводится** в dark.
`[data-theme="dark"]` использует generic slate sidebar для всех tenant'ов.
Brand identity в dark выражается только через `--brand-primary` chromatic
accent. Acceptable trade-off: cream-on-dark теряет premium-фактуру, проще
unify, чем поддерживать 4 палитры (light/dark × default/uzbekbank).

## Rationale

**Почему PDF не получает dark вариант**:

- **Print artifact**. Compliance отдел печатает досье — dark на бумаге
  расходует тонер ~6x light + неприятный bleed на cheap office paper.
- **Audit workflow**. Аудиторы CB РУз привыкли к white-paper layout
  десятилетиями. PDF — это **формальный документ кредитного решения**,
  не demo screen. Style consistency перевешивает personalization.
- **Engineering cost**. WeasyPrint templates (5 файлов в `templates/pdf/`)
  + matplotlib chart_renderer + 7-stage layout (cover/A-F-decision/audit).
  Полный re-skin = ~12-16 ч инженерного времени + risk regressions
  в audited print-flow. Не оправдано downstream-value'м.
- **Single source of truth**. PDF — это **снимок** на момент генерации.
  Theme=runtime UI choice. Смешивать = вводить ambiguity «какое досье
  правильное» в audit trail.

**Почему brand-primary остаётся константой**:

- Tenant identity (синий `#1E55C9` для default, в будущем `#2E1C16` для
  uzbekbank) — это **бренд**, не visual style. Shifting в dark на
  `#3D6FD8` (синяя more saturated) хоть и читался бы лучше, но
  отказывается от signal'а «вы у нас в системе X».
- Hover-вариант (`brand-primary-hover`) перевыставляется на lighter (а не
  darker, как в light) — это hover convention в dark mode (raised
  brightness, not deeper saturation).

**Почему system mode через live matchMedia listener**:

- Snapshot-on-mount подход (matchMedia читается только при init) ломает
  user expectations: OS включает auto-night-shift в 19:00, приложение
  открыто с обеда, ничего не меняется. Live listener покрывает этот
  сценарий за бесплатно (один `addEventListener` на mount + `removeEventListener`
  на unmount).

## Implementation sketch

1. `web/src/app/globals.css` — блок `[data-theme="dark"] {}` (~50 токенов:
   surface/-2/-3/bg, ink-1..4, border/-strong, sidebar/nav-*, state-{ok,warn,bad,info,neutral}-{fg,bg,border},
   brand-primary-soft/-hover/-ink/-ring, chart-1..5 + chart-{red,orange,yellow,green,blue,grey,grid,track,track-light},
   shadcn-defaults делегируются в semantic). `@media (prefers-color-scheme: dark) [data-theme="system"]` обёртка для первого paint.
2. `web/src/app/layout.tsx` — `<head>` inline blocking script читает
   `ca:settings:theme` из LS, проставляет `dataset.theme` до hydration.
   Закрывает FOUC при reload.
3. `web/src/features/settings/use-appearance.ts` — `useEffect` с
   `matchMedia('(prefers-color-scheme: dark)').addEventListener('change')`
   когда `theme === "system"`. Cleanup на unmount.
4. `web/src/features/settings/appearance-section.tsx` — убрать `disabled`
   с dark/system swatches, удалить `wipLabel` prop и i18n key
   `ap_theme_wip_sub`.
5. Audit ~104 hits `bg-white`/`text-white`/`bg-black`/`text-black`/hex literals в
   `web/src/**/*.{tsx,ts}` — заменить на semantic токены. ESLint
   `no-restricted-syntax` guard расширен на `src/app/**`.
6. Charts (recharts) — без изменений, уже используют `var(--chart-*)`.
7. Tests:
   - `use-appearance.test.ts`: 3 theme toggle + LS persist + applyToDocument
     + matchMedia subscribe/unsubscribe.
   - `appearance-section.test.tsx`: 3 swatch active, click меняет state
     + data-theme.
8. **Live-browser smoke перед merge** (lesson `feedback_nested_anchor_rtl_blind`):
   `/`, `/search`, `/history`, `/dossier/{id}`, `/help`, `/settings` ×
   3 темы. RTL/jsdom не ловят visual regressions.

## Known trade-offs

- **Segmented control visual hierarchy в dark**. Track использует
  `bg-[var(--surface-3)]` (`#1E242D` в dark), active pill `bg-[var(--surface)]`
  (`#0F1419` в dark). Active darker than track — inverted visual hierarchy
  vs light. Acceptable: legibility сохранена, design hole задокументирован.
  Полный фикс = split `surface-N` на `surface-elevated-N` и
  `surface-recessed-N` (отложен до Phase 11+).
- **uzbekbank dark = generic slate**. Cream-sidebar identity light-only.
- **`cookies()` в layout.tsx делает все routes dynamic** — уже принято
  в CA-DS29; dark-theme добавляет один inline script через `<head>`,
  не меняет static/dynamic flag.

## Consequences

- All `(bank)` routes теперь рендерятся в выбранной user-теме при первом
  paint (без FOUC).
- `(accountant)` mode сохраняет hardcoded dark identity sidebar — accountant
  использует dark-only design language, theme switch применим к main
  content, но sidebar не меняется.
- ESLint hex guard покрывает все runtime-pages — новые hardcoded `#XXX`
  будут блокироваться pre-commit. Исключения через `ignores` в
  `eslint.config.mjs` (swatch preview, QR canvas, accountant tenant identity).
- Future: тёмная PDF tail (если compliance запросит) — отдельный ADR-0014
  с migration plan для audit workflow. Не сейчас.
