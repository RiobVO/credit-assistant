# ADR 0011: UI mode differentiation strategy

- **Status**: Accepted
- **Date**: 2026-05-13
- **Phase**: post-4

## Context

ADR-0009 зафиксировал `APP_MODE`-based gating: один режим на установку (bank или
accountant), shared business core под двумя UI. Phase 4 закрыла Bank Mode UI и
накопила post-4 серию (CA-021..059), в которой несколько тикетов ввели
mode-conditional поведение и параллельный design-stack в shared слое:

- **Токены в `web/src/app/globals.css`**: два независимых набора —
  `--ca-*` (accountant legacy, navy + blue primary) и `--ub-*` (Uzbekbank
  bank-mode, slate ladder + terracotta accent). Каждый со своими
  surface/ink/border/state-tone тройками. Комментарий рядом честно фиксирует:
  «параллельно `--ca-*` (accountant остаётся на legacy). Не пересекаются».
- **Mode-conditional shells**: `AppShell` уже выбирает `BankSidebar` vs
  `AccountantSidebar` по `APP_MODE` (`web/src/components/app-shell.tsx`).
- **Mode-conditional features**:
  - CA-051 «+ Новая заявка» CTA в bank Sidebar
  - CA-052 history-aware back с mode-fallback
  - CA-055 sessionStorage `ca:dossier-back-target` с per-mode правилами
  - CA-058 borrower prefill только для bank-flow

Каждый тикет решал свою задачу, но без единой стратегии — `if (mode === 'bank')`
начинает протекать в shared компоненты, а два набора CSS-токенов де-факто
становятся двумя дизайн-системами. В процессе дизайн-ревью встал вопрос:
должны ли Bank и Accountant визуально различаться, или это один design с
разным брендом.

Без явной фиксации архитектурного invariant'а дрейф продолжится, и через 2
месяца получим два дизайн-системы без формального решения — и невозможность
честно выполнить инвариант PROJECT_BRIEF Section 2 «папа должен видеть, как
банк его увидел бы».

## Decision

**Один design system для обоих режимов.** Структурно (layout, spacing,
typography, components) Bank Mode и Accountant Mode идентичны. Различаются
три слоя — и только они:

### Brand layer

CSS-переменные из `config/brands/{tenant}.json`, loaded at boot based on
`APP_MODE` + `BRAND_ID` env:

- `--brand-primary` — primary цвет (Bank: navy под банк-tenant, Accountant:
  product color CreditAssistant)
- `--brand-logo-url` — путь к логотипу
- `--brand-name` — отображаемое название продукта
- `--brand-product-tagline` — сабтайтл под логотипом

Параллельные `--ca-*` и `--ub-*` сливаются в **единый semantic набор**
(`--surface`, `--ink-1/2/3`, `--border`, `--accent`, state tones), а
brand-специфичные значения переезжают под `--brand-*`. Tailwind theme
ссылается только на semantic-токены.

### Copy / microcopy

Mode-prefixed i18n keys через single `next-intl` provider:

- `bank.borrower.title` vs `accountant.my_company.title`
- `bank.cta.new_application` vs `accountant.cta.upload_files`
- Разные empty states, hints, banner texts

### Navigation / CTAs / feature visibility

`useAppMode()` hook возвращает mode на **top-level shells**: `AppShell`,
`Sidebar`, `ActionBar`. Ветвление допустимо **только** в shells.

**Запрещено:** `if (mode === ...)` глубже top-level shells. Если нужно
mode-aware поведение в shared компоненте — параметризовать через props или
derived data.

### Отступления от дизайн-исследования

Mockup-экспериментирование (CreditScope / Uzbekbank Credit) пробовало
разную эстетику между Bank Mode (navy + serious) и Accountant Mode
(lighter). От этого подхода отказываемся — он нарушает PROJECT_BRIEF
Section 2 invariant «папа должен видеть, как банк его увидел бы». Разный
design = непрозрачная разница между preview (Accountant) и реальностью
(Bank).

## Consequences

**Плюсы:**

- Один источник truth для design tokens (Tailwind theme + CSS vars из brand
  config).
- Per-bank whitelabel становится тривиальным: новый JSON в `config/brands/`,
  готово. Никакого UI-fork под каждый банк-tenant.
- Контракт «как банк увидел бы» сохраняется честно.
- Cognitive load при разработке падает: один visual mental model.

**Минусы:**

- Brand tokens добавляют indirection — нельзя `text-blue-600`, надо
  `text-[var(--brand-primary)]` или Tailwind-расширение.
- Mode-conditional логика концентрируется в top-level shells, делая их
  толще.
- Bank и Accountant теряют возможность визуально разойтись. Если в будущем
  появится product reason для расхождения — потребуется ADR, superseding
  этот.
- Миграция `--ca-*` / `--ub-*` → semantic + brand токены затронет почти
  все компоненты в `web/src/` (sweep по arbitrary-Tailwind значениям
  `[var(--ca-*)]` / `[var(--ub-*)]`).

**Что сделать дальше (Phase 5):**

- TODO[CA-060]: `config/brands/default.json` + `web/src/lib/brand.ts`
  provider с TypeScript-типами; semantic token layer в `globals.css`,
  миграция `--ca-*` / `--ub-*` callsites.
- TODO[CA-061]: audit post-4 тикетов (CA-051/052/055/058) на
  mode-conditional code outside top-level shells; refactor через props /
  `useAppMode()` только в shells.
- TODO[CA-062]: ESLint rule запрещающая hardcoded hex/rgb в
  `web/src/features/**` и `web/src/components/**` (allowed only в
  `web/src/lib/brand.ts` и token defs `globals.css`).
- TODO[CA-063]: i18n key naming — переименовать `borrower.*` ключи в
  `bank.borrower.*` и `accountant.my_company.*` (breaking, sweep всех
  call-site'ов).

## References

- `PROJECT_BRIEF.md` Section 2 — Two Operating Modes (Critical). Invariant
  «папа видит как банк увидел бы».
- `PROJECT_BRIEF.md` Section 4 — «два UI поверх одного бизнес-ядра».
- ADR-0009 — Bank Mode и `APP_MODE` gating.
- `CLAUDE.md` «Активные договорённости» — CA-051, CA-052, CA-055, CA-058
  как примеры существующего mode-conditional drift'а.
- `web/src/app/globals.css` — текущие параллельные `--ca-*` / `--ub-*`
  наборы (источник drift'а на уровне токенов).
- `web/src/components/app-shell.tsx` — существующий top-level
  `APP_MODE`-switch (соответствует целевому invariant'у).
- Industry pattern: multi-tenant single design system + brand tokens
  (Linear, Notion, GitHub Enterprise).
