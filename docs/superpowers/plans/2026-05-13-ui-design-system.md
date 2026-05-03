# UI Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each phase ends with a verify-gate (tsc + eslint + vitest + build); do not advance until green.

**Goal:** Перевести `web/` на единый design system с brand-layer (под invariant ADR-0011), закрыть критические UX-пробелы (error boundaries, JetBrains Mono для чисел, auto-save индикатор, inline helpers, ⌘K global search, redesigned Bank login), добавить демо-сид с realistic UZ MSB borrowers — без касания PDF, mobile responsive, кастомных animations.

**Architecture:** Один design system для bank + accountant, brand-tenant через `config/brands/{tenant}.json` (ADR-0011). Параллельные `--ca-*` / `--ub-*` token-наборы в `web/src/app/globals.css` сливаются в один semantic слой (`--surface`, `--ink-1/2/3`, `--border`, `--accent`, state tones); brand-специфика выезжает под `--brand-*`. Tailwind theme ссылается только на semantic-токены. Mode-conditional ветвление допускается только в top-level shells (`AppShell`, `Sidebar`, `Topbar`, `ActionBar`) через `useAppMode()` hook.

**Tech Stack:** Next.js 16.2.6 (App Router), React 19.2.4, TypeScript strict, Tailwind 4, shadcn (через `shadcn` 4.7), TanStack Query 5, react-hook-form 7 + zod 4, vitest 3 + RTL 16, lucide-react.

**Ground rules for the implementing engineer:**
- **Do not skip TDD-шаги.** Где тест указан — пиши тест первым, прогоняй на FAIL, потом имплементируй, прогоняй на PASS.
- **Не лезь за scope фазы.** Если в Phase 1 видишь баг в Phase 4 коде — записывай в TODO[CA-XXX] и двигайся.
- **Verify после каждой фазы:** `cd web && npm run lint && npx tsc --noEmit && npm run test:run && npm run build` — все 4 зелёные. На backend-фазах (Phase 7 seed): `uv run pytest -q`.
- **Коммит — атомарный.** Один таск = один коммит с conventional prefix (`feat`, `refactor`, `chore`, `test`). Не складывай 3 таска в один commit.
- **PowerShell на хосте, Bash в Docker.** Команды ниже — PowerShell-совместимые; если копируешь в Bash WSL — пути сами адаптируешь.
- **Реальные пути из репо.** Если файл по указанному пути не существует — стоп, не угадывай, спроси / зачитай `MEMORY.md` / спроси user.
- **Не трогай PDF, mobile responsive, animations.** Эти три зоны явно out-of-scope этого плана.

---

## Phase Map (≈6 рабочих дней)

| # | Phase | ETA | Blocking? |
|---|---|---|---|
| 0 | Commit ADR-0011 | 10 мин | блокирует всё (формальный invariant) |
| 1 | Semantic + brand tokens (CA-060) | 1.5 дня | блокирует 2,3,4,5,6 |
| 2 | ESLint guard (CA-062) | 1 ч | блокирует уверенность что drift не вернётся |
| 3 | Mode-conditional audit (CA-061) | 0.5 дня | независимо |
| 4 | Topbar global + error boundaries | 1 день | независимо |
| 5 | KPI/manual-input polish | 1 день | независимо |
| 6 | Bank login redesign | 0.5 дня | независимо |
| 7 | Demo seed (backend) | 0.5 дня | независимо |
| 8 | Quarterly tables audit + add | 0.5–1 день | независимо |
| 9 | i18n keys naming (CA-063) | 1 день | после shells (4) |

Phase 3–8 параллелизуемы между собой после Phase 1. Phase 9 откладывается до закрытия Phase 4.

---

## Phase 0: Commit ADR-0011

ADR-0011 принят, дата 2026-05-13, но `docs/adr/0011-ui-mode-differentiation.md` сейчас untracked. Без него весь sweep tokens идёт без формальной фиксации invariant'а «один design system, brand через config».

**Files:**
- Stage: `docs/adr/0011-ui-mode-differentiation.md`

- [ ] **Step 0.1: Verify ADR exists and is untracked**

Run: `git status docs/adr/0011-ui-mode-differentiation.md`
Expected: `?? docs/adr/0011-ui-mode-differentiation.md` (untracked).
Если уже committed — пропусти Phase 0 целиком, двигайся к Phase 1.

- [ ] **Step 0.2: Stage and commit**

```powershell
git add docs/adr/0011-ui-mode-differentiation.md
git commit -m "docs(adr): 0011 — one design system + brand-layer invariant"
```

- [ ] **Step 0.3: Verify**

Run: `git log -1 --name-only`
Expected: HEAD commit показывает `docs/adr/0011-ui-mode-differentiation.md`.

---

## Phase 1: Semantic + brand tokens (CA-060)

`web/src/app/globals.css` сейчас содержит два параллельных набора: `--ca-*` (accountant legacy) и `--ub-*` (Uzbekbank bank-mode), плюс shadcn-defaults (`--background`, `--primary`, ...). Цель — единый semantic слой + brand слой, на который смотрит Tailwind theme и весь callsite.

**Token mapping (semantic → tenant-specific сегодня)**

| Semantic | Bank tenant (`uzbekbank`) | Accountant tenant (`default`) |
|---|---|---|
| `--surface` | `#FFFFFF` | `#FCFCFD` |
| `--surface-2` | `#F8FAFC` | `#FAFBFC` |
| `--surface-3` | `#F1F5F9` | `#F1F5F9` |
| `--bg` | `#F1F5F9` | `#F1F5F9` |
| `--ink-1` | `#0F172A` | `#0E1525` |
| `--ink-2` | `#475569` | `#2B3344` |
| `--ink-3` | `#64748B` | `#5A6478` |
| `--ink-4` | `#94A3B8` | `#7A8497` |
| `--border` | `#E2E8F0` | `#E4E7EC` |
| `--border-strong` | `#CBD5E1` | `#CDD3DD` |
| `--brand-primary` | `#CC785C` (terracotta) | `#1E55C9` (blue) |
| `--brand-primary-hover` | `#B5624A` | `#1947AA` |
| `--brand-primary-soft` | `#F7E8DF` | `#EAF0FB` |
| `--brand-primary-ink` | `#6E2F1C` | `#1947AA` |
| `--brand-ring` | `rgba(204,120,92,0.22)` | `rgba(30,85,201,0.22)` |
| `--brand-name` | `"Uzbekbank Credit"` | `"Credit Assistant"` |
| `--brand-product-tagline` | `"Bank Mode"` | `"Accountant Mode"` |
| `--brand-logo-mark` | `"UB"` | `"CA"` |
| `--nav-bg` | `#0B1220` | `#0B1220` |
| `--nav-bg-2` | `#0F172A` | `#111A2E` |
| `--nav-bg-hover` | `#1E293B` | `#1F2D47` |
| `--nav-border` | `#1E293B` | `#243049` |
| `--nav-text` | `#E2E8F0` | `#E6EAF2` |
| `--nav-text-2` | `#94A3B8` | `#8A95AC` |
| `--nav-text-3` | `#64748B` | `#5C6884` |
| `--state-ok-fg` / `--state-ok-bg` | `#166534` / `#DCFCE7` | `#0F8A5F` / `#E6F4EE` |
| `--state-warn-fg` / `--state-warn-bg` | `#92400E` / `#FEF3C7` | `#B8730E` / `#FFF6E5` |
| `--state-bad-fg` / `--state-bad-bg` | `#991B1B` / `#FEE2E2` | `#B42318` / `#FCE7E5` |
| `--state-info-fg` / `--state-info-bg` | `#6E2F1C` / `#F7E8DF` | `#1947AA` / `#EAF0FB` |
| `--state-neutral-fg` / `--state-neutral-bg` | `#334155` / `#F1F5F9` | `#5A6478` / `#FAFBFC` |

**Files:**
- Create: `config/brands/default.json`, `config/brands/uzbekbank.json`
- Create: `web/src/lib/brand.ts`
- Create: `web/src/lib/brand.test.ts`
- Modify: `web/src/app/globals.css` (полная переработка `:root` + `@theme inline`)
- Modify: `web/src/app/layout.tsx` (JetBrains Mono font + brand class на `<html>`)
- Modify: `web/src/lib/config.ts` (добавить `BRAND_ID`)
- Sweep: все файлы под `web/src/` использующие `var(--ca-*)` или `var(--ub-*)`

---

### Task 1.1: Brand config schema + loader

- [ ] **Step 1.1.1: Write failing test for brand schema**

Create `web/src/lib/brand.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { brandSchema, loadBrandFromJson } from "./brand";

describe("brand", () => {
  it("validates a full brand config", () => {
    const raw = {
      id: "default",
      name: "Credit Assistant",
      tagline: "Accountant Mode",
      logoMark: "CA",
      primary: "#1E55C9",
      primaryHover: "#1947AA",
      primarySoft: "#EAF0FB",
      primaryInk: "#1947AA",
      primaryRing: "rgba(30,85,201,0.22)",
    };
    expect(() => brandSchema.parse(raw)).not.toThrow();
  });

  it("rejects invalid hex", () => {
    const raw = {
      id: "x",
      name: "x",
      tagline: "x",
      logoMark: "X",
      primary: "not-a-hex",
      primaryHover: "#000000",
      primarySoft: "#000000",
      primaryInk: "#000000",
      primaryRing: "rgba(0,0,0,1)",
    };
    expect(() => brandSchema.parse(raw)).toThrow();
  });

  it("loads brand from raw JSON object", () => {
    const brand = loadBrandFromJson({
      id: "default",
      name: "Credit Assistant",
      tagline: "Accountant Mode",
      logoMark: "CA",
      primary: "#1E55C9",
      primaryHover: "#1947AA",
      primarySoft: "#EAF0FB",
      primaryInk: "#1947AA",
      primaryRing: "rgba(30,85,201,0.22)",
    });
    expect(brand.id).toBe("default");
    expect(brand.cssVars["--brand-primary"]).toBe("#1E55C9");
  });
});
```

- [ ] **Step 1.1.2: Run test, verify FAIL**

Run: `cd web && npx vitest run src/lib/brand.test.ts`
Expected: FAIL (`brand.ts` not found).

- [ ] **Step 1.1.3: Implement brand.ts**

Create `web/src/lib/brand.ts`:

```typescript
import { z } from "zod";

const hex = z.string().regex(/^#[0-9A-Fa-f]{6}$/, "must be #RRGGBB");
const rgba = z.string().regex(/^rgba\(\s*\d+,\s*\d+,\s*\d+,\s*[0-9.]+\)$/, "must be rgba(r,g,b,a)");

export const brandSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  tagline: z.string(),
  logoMark: z.string().min(1).max(4),
  primary: hex,
  primaryHover: hex,
  primarySoft: hex,
  primaryInk: hex,
  primaryRing: rgba,
});

export type BrandConfig = z.infer<typeof brandSchema>;

export type Brand = {
  id: string;
  name: string;
  tagline: string;
  logoMark: string;
  cssVars: Record<string, string>;
};

export function loadBrandFromJson(raw: unknown): Brand {
  const cfg = brandSchema.parse(raw);
  return {
    id: cfg.id,
    name: cfg.name,
    tagline: cfg.tagline,
    logoMark: cfg.logoMark,
    cssVars: {
      "--brand-primary": cfg.primary,
      "--brand-primary-hover": cfg.primaryHover,
      "--brand-primary-soft": cfg.primarySoft,
      "--brand-primary-ink": cfg.primaryInk,
      "--brand-primary-ring": cfg.primaryRing,
    },
  };
}

import defaultJson from "../../../config/brands/default.json";
import uzbekbankJson from "../../../config/brands/uzbekbank.json";

const REGISTRY: Record<string, Brand> = {
  default: loadBrandFromJson(defaultJson),
  uzbekbank: loadBrandFromJson(uzbekbankJson),
};

export function resolveBrand(brandId: string | undefined): Brand {
  if (brandId && REGISTRY[brandId]) return REGISTRY[brandId];
  return REGISTRY.default;
}
```

- [ ] **Step 1.1.4: Create brand JSON configs**

Create `config/brands/default.json`:

```json
{
  "id": "default",
  "name": "Credit Assistant",
  "tagline": "Accountant Mode",
  "logoMark": "CA",
  "primary": "#1E55C9",
  "primaryHover": "#1947AA",
  "primarySoft": "#EAF0FB",
  "primaryInk": "#1947AA",
  "primaryRing": "rgba(30,85,201,0.22)"
}
```

Create `config/brands/uzbekbank.json`:

```json
{
  "id": "uzbekbank",
  "name": "Uzbekbank Credit",
  "tagline": "Bank Mode",
  "logoMark": "UB",
  "primary": "#CC785C",
  "primaryHover": "#B5624A",
  "primarySoft": "#F7E8DF",
  "primaryInk": "#6E2F1C",
  "primaryRing": "rgba(204,120,92,0.22)"
}
```

- [ ] **Step 1.1.5: Configure tsconfig to import JSON**

Verify `web/tsconfig.json` has `"resolveJsonModule": true` (Next.js default). If not, add it.

- [ ] **Step 1.1.6: Run test, verify PASS**

Run: `cd web && npx vitest run src/lib/brand.test.ts`
Expected: 3 passed.

- [ ] **Step 1.1.7: Commit**

```powershell
git add config/brands/ web/src/lib/brand.ts web/src/lib/brand.test.ts
git commit -m "feat(web): brand config schema + uzbekbank/default tenants (CA-060)"
```

---

### Task 1.2: Add `BRAND_ID` env + config getter

- [ ] **Step 1.2.1: Modify `web/src/lib/config.ts`**

Read current file first: `cat web/src/lib/config.ts` (or Read tool). Append after existing exports:

```typescript
export const BRAND_ID: string =
  process.env.NEXT_PUBLIC_BRAND_ID ??
  (APP_MODE === "bank" ? "uzbekbank" : "default");
```

(`APP_MODE` уже экспортируется в config.ts; если нет — добавь и его.)

- [ ] **Step 1.2.2: Verify build**

Run: `cd web && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 1.2.3: Commit**

```powershell
git add web/src/lib/config.ts
git commit -m "feat(web): BRAND_ID resolver from env + APP_MODE (CA-060)"
```

---

### Task 1.3: Add JetBrains Mono font

- [ ] **Step 1.3.1: Read current `web/src/app/layout.tsx`**

- [ ] **Step 1.3.2: Replace font-mono with JetBrains Mono**

Inside `web/src/app/layout.tsx`, alongside existing `next/font` imports, add:

```typescript
import { Inter, JetBrains_Mono } from "next/font/google";

const fontSans = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-sans",
  display: "swap",
});

const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});
```

And on the `<html>` element apply: `className={`${fontSans.variable} ${fontMono.variable}`}`.

(Adjust to whatever font import pattern already exists; if `Inter` is already imported, just add `JetBrains_Mono` next to it.)

- [ ] **Step 1.3.3: Apply brand via root attribute**

In the same `layout.tsx`, import `BRAND_ID` from `@/lib/config` and `resolveBrand` from `@/lib/brand`:

```typescript
import { BRAND_ID } from "@/lib/config";
import { resolveBrand } from "@/lib/brand";

// inside RootLayout:
const brand = resolveBrand(BRAND_ID);
const brandStyle = Object.entries(brand.cssVars)
  .map(([k, v]) => `${k}:${v}`)
  .join(";");

// pass to <html>:
<html lang="ru" style={brandStyle} data-brand={brand.id}>
```

- [ ] **Step 1.3.4: Verify font loads in dev**

Run `cd web && npm run dev` in background. Open `http://localhost:3000`. Open devtools → Computed styles на любом `<span class="font-mono">` → должен быть `JetBrains Mono`. Стопни dev server.

- [ ] **Step 1.3.5: Commit**

```powershell
git add web/src/app/layout.tsx
git commit -m "feat(web): JetBrains Mono font + brand cssVars on <html> (CA-060)"
```

---

### Task 1.4: Add semantic + brand token layer to `globals.css` (non-breaking phase)

В этой задаче добавляем новые семантические переменные **параллельно** существующим `--ca-*` / `--ub-*`. Это даёт нам безопасный sweep — пока ничего не ломается, потом перетягиваем callsites, и только тогда удаляем старые.

- [ ] **Step 1.4.1: Read current `web/src/app/globals.css`**

- [ ] **Step 1.4.2: Append semantic + brand layer**

В `:root` блоке (после существующих `--ub-*` переменных, перед закрывающей `}`) добавь:

```css
  /* ── Semantic layer (CA-060) — единственный источник для UI кода. ──
     Tenant-specific значения здесь — для default (accountant); bank-tenant
     переопределяет их в [data-brand="uzbekbank"] блоке ниже. */
  --surface: #FCFCFD;
  --surface-2: #FAFBFC;
  --surface-3: #F1F5F9;
  --bg: #F1F5F9;

  --ink-1: #0E1525;
  --ink-2: #2B3344;
  --ink-3: #5A6478;
  --ink-4: #7A8497;

  --border: #E4E7EC;
  --border-strong: #CDD3DD;

  --nav-bg: #0B1220;
  --nav-bg-2: #111A2E;
  --nav-bg-hover: #1F2D47;
  --nav-border: #243049;
  --nav-text: #E6EAF2;
  --nav-text-2: #8A95AC;
  --nav-text-3: #5C6884;

  --state-ok-fg: #0F8A5F;  --state-ok-bg: #E6F4EE;
  --state-warn-fg: #B8730E; --state-warn-bg: #FFF6E5;
  --state-bad-fg: #B42318;  --state-bad-bg: #FCE7E5;
  --state-info-fg: #1947AA; --state-info-bg: #EAF0FB;
  --state-neutral-fg: #5A6478; --state-neutral-bg: #FAFBFC;

  /* Brand fallback (для случаев когда brand-cssVars не загружены) */
  --brand-primary: #1E55C9;
  --brand-primary-hover: #1947AA;
  --brand-primary-soft: #EAF0FB;
  --brand-primary-ink: #1947AA;
  --brand-primary-ring: rgba(30, 85, 201, 0.22);
}

/* Bank-tenant overrides (когда <html data-brand="uzbekbank">) */
:root[data-brand="uzbekbank"] {
  --surface: #FFFFFF;
  --surface-2: #F8FAFC;
  --ink-1: #0F172A;
  --ink-2: #475569;
  --ink-3: #64748B;
  --ink-4: #94A3B8;
  --border: #E2E8F0;
  --border-strong: #CBD5E1;
  --nav-bg-2: #0F172A;
  --nav-bg-hover: #1E293B;
  --nav-border: #1E293B;
  --nav-text: #E2E8F0;
  --nav-text-2: #94A3B8;
  --nav-text-3: #64748B;
  --state-ok-fg: #166534; --state-ok-bg: #DCFCE7;
  --state-warn-fg: #92400E; --state-warn-bg: #FEF3C7;
  --state-bad-fg: #991B1B;  --state-bad-bg: #FEE2E2;
  --state-info-fg: #6E2F1C; --state-info-bg: #F7E8DF;
  --state-neutral-fg: #334155; --state-neutral-bg: #F1F5F9;
```

- [ ] **Step 1.4.3: Register semantic tokens in `@theme inline`**

В `@theme inline { ... }` блоке (после уже существующих `--color-ub-*`) добавь:

```css
  --color-surface: var(--surface);
  --color-surface-2: var(--surface-2);
  --color-surface-3: var(--surface-3);
  --color-bg: var(--bg);
  --color-ink-1: var(--ink-1);
  --color-ink-2: var(--ink-2);
  --color-ink-3: var(--ink-3);
  --color-ink-4: var(--ink-4);
  --color-border-semantic: var(--border);
  --color-border-strong: var(--border-strong);
  --color-nav-bg: var(--nav-bg);
  --color-nav-bg-2: var(--nav-bg-2);
  --color-nav-bg-hover: var(--nav-bg-hover);
  --color-nav-border: var(--nav-border);
  --color-nav-text: var(--nav-text);
  --color-nav-text-2: var(--nav-text-2);
  --color-nav-text-3: var(--nav-text-3);
  --color-state-ok-fg: var(--state-ok-fg);
  --color-state-ok-bg: var(--state-ok-bg);
  --color-state-warn-fg: var(--state-warn-fg);
  --color-state-warn-bg: var(--state-warn-bg);
  --color-state-bad-fg: var(--state-bad-fg);
  --color-state-bad-bg: var(--state-bad-bg);
  --color-state-info-fg: var(--state-info-fg);
  --color-state-info-bg: var(--state-info-bg);
  --color-state-neutral-fg: var(--state-neutral-fg);
  --color-state-neutral-bg: var(--state-neutral-bg);
  --color-brand-primary: var(--brand-primary);
  --color-brand-primary-hover: var(--brand-primary-hover);
  --color-brand-primary-soft: var(--brand-primary-soft);
  --color-brand-primary-ink: var(--brand-primary-ink);
```

Note: `--color-border-semantic` (а не `--color-border`) — `--color-border` уже занят shadcn-defaults.

- [ ] **Step 1.4.4: Verify build still green**

Run: `cd web && npm run build`
Expected: build succeeds.

- [ ] **Step 1.4.5: Commit**

```powershell
git add web/src/app/globals.css
git commit -m "feat(web): semantic + brand token layer (parallel to --ca-*/--ub-*) (CA-060)"
```

---

### Task 1.5: Sweep `--ca-*` → semantic

- [ ] **Step 1.5.1: List all `--ca-*` callsites**

Run (PowerShell):

```powershell
cd web
git grep -n "var(--ca-" src/ > ../_sweep_ca.txt
```

Expected: file with ~80–150 hits (KPI cards, sidebars, dossier-skeleton, etc).

- [ ] **Step 1.5.2: Build mapping table**

Используй эту таблицу. **Каждый `var(--ca-X)` → `var(--SEMANTIC)`:**

| Old | New |
|---|---|
| `--ca-bg` | `--bg` |
| `--ca-surface` | `--surface` |
| `--ca-border` | `--border` |
| `--ca-border-strong` | `--border-strong` |
| `--ca-ink-900` | `--ink-1` |
| `--ca-ink-700` | `--ink-2` |
| `--ca-ink-500` | `--ink-3` |
| `--ca-ink-400` | `--ink-4` |
| `--ca-navy-900` | `--nav-bg` |
| `--ca-navy-800` | `--nav-bg-2` |
| `--ca-navy-700` | `--nav-bg-2` (fold up) |
| `--ca-navy-600` | `--nav-bg-hover` |
| `--ca-navy-500` | `--nav-bg-hover` (fold) |
| `--ca-line-dark` | `--nav-border` |
| `--ca-muted-dark` | `--nav-text-2` |
| `--ca-muted-dark-2` | `--nav-text-3` |
| `--ca-primary-blue` | `--brand-primary` |
| `--ca-primary-blue-700` | `--brand-primary-hover` |
| `--ca-primary-blue-50` | `--brand-primary-soft` |
| `--ca-success` | `--state-ok-fg` |
| `--ca-success-50` | `--state-ok-bg` |
| `--ca-warning` | `--state-warn-fg` |
| `--ca-danger` | `--state-bad-fg` |

- [ ] **Step 1.5.3: Run replace per mapping**

PowerShell — для каждой строки маппинга:

```powershell
# Пример для одной пары
Get-ChildItem -Path web/src -Recurse -Include *.tsx,*.ts,*.css `
  | ForEach-Object {
    (Get-Content $_.FullName -Raw) `
      -replace '--ca-bg\b', '--bg' `
      | Set-Content -NoNewline $_.FullName
  }
```

Повторить для каждой пары из таблицы. Или одной командой sed-style через Edit-tool по списку файлов из `_sweep_ca.txt`.

**Edge cases:**
- Не трогай файлы в `web/design-reference/` (там mockup'ы, не реальный код).
- Не трогай комментарии — `replace_all` глобальный, но если строка только в комментарии, безопасно.

- [ ] **Step 1.5.4: Verify zero remaining `--ca-*` references**

Run: `cd web && git grep -n "var(--ca-" src/`
Expected: empty output.

- [ ] **Step 1.5.5: Verify build + tests still green**

```powershell
cd web
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```
Expected: 0 errors, 0 lint warnings, tests pass.

- [ ] **Step 1.5.6: Commit**

```powershell
git add web/src
git commit -m "refactor(web): sweep --ca-* → semantic tokens (CA-060)"
```

---

### Task 1.6: Sweep `--ub-*` → semantic + brand

- [ ] **Step 1.6.1: List `--ub-*` callsites**

```powershell
cd web
git grep -n "var(--ub-" src/ > ../_sweep_ub.txt
```

- [ ] **Step 1.6.2: Mapping table**

| Old | New |
|---|---|
| `--ub-bg` | `--surface` |
| `--ub-surface` | `--surface` |
| `--ub-surface-2` | `--surface-2` |
| `--ub-surface-3` | `--surface-3` |
| `--ub-hairline` | `--border` |
| `--ub-hairline-soft` | `--border` (fold, или новый `--border-soft` если визуально критично — judge call по diff) |
| `--ub-nav-bg` | `--nav-bg` |
| `--ub-nav-bg-2` | `--nav-bg-2` |
| `--ub-nav-bg-hover` | `--nav-bg-hover` |
| `--ub-nav-border` | `--nav-border` |
| `--ub-nav-active-bg` | `--nav-bg-hover` (fold) |
| `--ub-nav-text` | `--nav-text` |
| `--ub-nav-text-2` | `--nav-text-2` |
| `--ub-nav-text-3` | `--nav-text-3` |
| `--ub-ink` | `--ink-1` |
| `--ub-ink-2` | `--ink-2` |
| `--ub-ink-3` | `--ink-3` |
| `--ub-ink-4` | `--ink-4` |
| `--ub-accent` | `--brand-primary` |
| `--ub-accent-hover` | `--brand-primary-hover` |
| `--ub-accent-soft` | `--brand-primary-soft` |
| `--ub-accent-ink` | `--brand-primary-ink` |
| `--ub-accent-ring` | `--brand-primary-ring` |
| `--ub-ok-fg` / `--ub-ok-bg` | `--state-ok-fg` / `--state-ok-bg` |
| `--ub-warn-fg` / `--ub-warn-bg` | `--state-warn-fg` / `--state-warn-bg` |
| `--ub-bad-fg` / `--ub-bad-bg` | `--state-bad-fg` / `--state-bad-bg` |
| `--ub-info-fg` / `--ub-info-bg` | `--state-info-fg` / `--state-info-bg` |
| `--ub-neutral-fg` / `--ub-neutral-bg` | `--state-neutral-fg` / `--state-neutral-bg` |

- [ ] **Step 1.6.3: Run replace**

(Аналогично 1.5.3 — PowerShell loop по таблице.)

- [ ] **Step 1.6.4: Verify zero `--ub-*` references**

Run: `cd web && git grep -n "var(--ub-" src/`
Expected: empty.

- [ ] **Step 1.6.5: Verify still green**

```powershell
cd web
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

- [ ] **Step 1.6.6: Commit**

```powershell
git add web/src
git commit -m "refactor(web): sweep --ub-* → semantic + brand tokens (CA-060)"
```

---

### Task 1.7: Remove `--ca-*` / `--ub-*` from `globals.css`

- [ ] **Step 1.7.1: Delete old token definitions**

В `web/src/app/globals.css`:
1. Удали все `--ca-*` строки из `:root`.
2. Удали все `--ub-*` строки из `:root`.
3. Удали все `--color-ca-*` и `--color-ub-*` строки из `@theme inline`.
4. Не трогай shadcn-defaults (`--background`, `--primary`, `--card`, etc.) — они остаются для совместимости с shadcn-компонентами.

- [ ] **Step 1.7.2: Update shadcn `--primary` to delegate to brand**

Замени:

```css
--primary: #1E55C9;
```

на:

```css
--primary: var(--brand-primary);
```

И аналогично:

```css
--ring: var(--brand-primary);
--accent: var(--brand-primary-soft);
--accent-foreground: var(--brand-primary-ink);
```

Это даёт shadcn-компонентам автоматически тянуть brand.

- [ ] **Step 1.7.3: Verify final build**

```powershell
cd web
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```
Expected: 0 errors.

- [ ] **Step 1.7.4: Manual visual check**

Запусти dev server, открой:
- `/login` (bank-tenant: должен быть terracotta accent на кнопке)
- `/manual-input` (default-tenant: blue accent)
- `/dossier/<any-id>` (если есть test dossier)

Убедись что нет «голых» белых блоков от потерянных переменных. Стопни dev server.

- [ ] **Step 1.7.5: Commit**

```powershell
git add web/src/app/globals.css
git commit -m "refactor(web): remove legacy --ca-*/--ub-* tokens, delegate to brand (CA-060)"
```

---

## Phase 2: ESLint guard (CA-062)

Запрет hardcoded `#hex` / `rgb()` / `rgba()` в `web/src/features/**` и `web/src/components/**` — единственные allowed места: `web/src/lib/brand.ts`, `web/src/app/globals.css`. Это гейт чтобы token-миграция не размывалась future-коммитами.

**Files:**
- Modify: `web/eslint.config.mjs`
- Create: `web/eslint-tests/no-hardcoded-colors.test.tsx` (canary file для проверки правила)

---

### Task 2.1: Add `no-restricted-syntax` rule

- [ ] **Step 2.1.1: Modify `web/eslint.config.mjs`**

Замени тело файла на:

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    files: ["src/features/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          // Запрет hardcoded hex в JSX/style values.
          // Allowed: var(--*), theme классы, evidence chart-цвета (через
          // semantic токены или brand vars).
          selector: "Literal[value=/^#[0-9A-Fa-f]{3,8}$/]",
          message:
            "Hardcoded hex запрещён в features/components. Используй var(--*) из globals.css или brand токены. См. ADR-0011.",
        },
        {
          selector: "TemplateElement[value.raw=/#[0-9A-Fa-f]{6}/]",
          message: "Hardcoded hex в template literal запрещён. Используй var(--*).",
        },
        {
          selector: "Literal[value=/^rgba?\\(/]",
          message: "Hardcoded rgb/rgba запрещён. Используй var(--*) или brand токены.",
        },
      ],
    },
  },
]);

export default eslintConfig;
```

- [ ] **Step 2.1.2: Run lint to check no false-positives on current code**

```powershell
cd web
npm run lint
```

Expected: 0 errors. Если есть violations — это **существующие** hardcoded hex после Phase 1 sweep'а (например в `score-gauge.tsx` строки 9-14 — `#B42318`, `#E07A2A`, `#D4A815`, `#0F8A5F`). Эти **не** удаляются автоматически в Phase 1 (там был только `var(--*)` sweep). Если они есть — это значит chart-цвета. Действие:
  1. Добавь в `:root` чарт-токены: `--chart-red: #B42318; --chart-orange: #E07A2A; --chart-yellow: #D4A815; --chart-green: #0F8A5F;`
  2. Перепиши `score-gauge.tsx:9-14` на использование этих токенов.
  3. Перезапусти lint.

- [ ] **Step 2.1.3: Verify rule actually fires (canary)**

Create `web/eslint-tests/no-hardcoded-colors.test.tsx`:

```tsx
// Этот файл нужен только для smoke-проверки ESLint правила.
// Должен быть под `web/src/features/__canary__/` чтобы попасть под правило.
export function Canary() {
  return <div style={{ color: "#FF0000" }}>canary</div>;
}
```

Move it: `mv web/eslint-tests/no-hardcoded-colors.test.tsx web/src/features/__canary__/canary.tsx`

Run: `cd web && npm run lint`
Expected: ERROR на `canary.tsx` с сообщением о hardcoded hex.

- [ ] **Step 2.1.4: Remove canary**

```powershell
Remove-Item -Recurse web/src/features/__canary__
```

Re-run `npm run lint` → 0 errors.

- [ ] **Step 2.1.5: Commit**

```powershell
git add web/eslint.config.mjs
git commit -m "chore(web): ESLint rule banning hardcoded hex/rgb in features+components (CA-062)"
```

---

## Phase 3: Mode-conditional audit (CA-061)

ADR-0011: «`if (mode === ...)` глубже top-level shells запрещён». Sweep по post-4 тикетам CA-051/052/055/058 + `parseManualInputView`/`back-target`/etc.

**Files:**
- Create: `web/src/lib/use-app-mode.ts`
- Modify (audit only): `web/src/features/dossier/back-target.ts`, `web/src/features/dossier/action-bar.tsx`, `web/src/features/manual-input/prefill.ts`, `web/src/features/manual-input/manual-input-view.tsx`, `web/src/app/(bank)/_components/sidebar.tsx`, `web/src/app/(accountant)/_components/sidebar.tsx`

---

### Task 3.1: Audit current mode-conditional callsites

- [ ] **Step 3.1.1: Find all callsites**

```powershell
cd web
git grep -n "APP_MODE" src/
git grep -nE "mode\s*===\s*['\"]bank['\"]|mode\s*===\s*['\"]accountant['\"]" src/
```

Expected: список ~5-15 hits.

- [ ] **Step 3.1.2: Classify each hit**

Для каждого hit ответь:
- **Top-level shell?** (AppShell, Sidebar, Topbar, ActionBar, root layout) — допустимо.
- **Shared component / feature?** — нарушение. Нужен refactor.

Запиши классификацию в комментарий PR-описания (или в `_audit_notes.md` локально).

### Task 3.2: Create `useAppMode()` hook

- [ ] **Step 3.2.1: Write failing test**

Create `web/src/lib/use-app-mode.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAppMode } from "./use-app-mode";

vi.mock("./config", () => ({ APP_MODE: "bank" }));

describe("useAppMode", () => {
  it("returns APP_MODE from config", () => {
    const { result } = renderHook(() => useAppMode());
    expect(result.current).toBe("bank");
  });
});
```

- [ ] **Step 3.2.2: Run, verify FAIL**

`cd web && npx vitest run src/lib/use-app-mode.test.ts`
Expected: FAIL.

- [ ] **Step 3.2.3: Implement**

Create `web/src/lib/use-app-mode.ts`:

```typescript
import { APP_MODE } from "./config";

export type AppMode = "bank" | "accountant";

export function useAppMode(): AppMode {
  return APP_MODE as AppMode;
}
```

(Хук вместо прямого импорта `APP_MODE` — чтобы при будущем переходе на runtime config / context API call-site не менялся.)

- [ ] **Step 3.2.4: Run, verify PASS**

Expected: 1 passed.

- [ ] **Step 3.2.5: Commit**

```powershell
git add web/src/lib/use-app-mode.ts web/src/lib/use-app-mode.test.ts
git commit -m "feat(web): useAppMode() hook for top-level shell branching (CA-061)"
```

### Task 3.3: Refactor leaks из audit

Для каждого hit из 3.1.2, который НЕ в top-level shell:

- [ ] **Step 3.3.1: Refactor through props**

Пример: если `back-target.ts:25` имеет `if (APP_MODE === 'bank') { fallback = '/history' } else { fallback = '/manual-input' }`, перепиши на:

```typescript
export function consumeBackTarget(fallback: string): string {
  // ... existing logic ...
  return targetFromStorage ?? fallback;
}
```

И в callsite (top-level `ActionBar` / `AppShell` / page-component) пробрось `fallback` из `useAppMode()`:

```typescript
const mode = useAppMode();
const fallback = mode === "bank" ? "/history" : "/manual-input";
consumeBackTarget(fallback);
```

- [ ] **Step 3.3.2: Per-file commit**

Один коммит на файл, prefix `refactor(web)`, message формы: `refactor(web): lift APP_MODE из <feature> в top-level shell (CA-061)`.

- [ ] **Step 3.3.3: Verify все callsites чистые**

```powershell
cd web
# В features/ и components/ не должно быть APP_MODE или хука useAppMode (только в shells)
git grep -n "useAppMode\|APP_MODE" src/features src/components/ui
```
Expected: пусто. Если что-то осталось — повтори 3.3.1 для этого файла.

- [ ] **Step 3.3.4: Verify**

```powershell
cd web
npm run lint
npx tsc --noEmit
npm run test:run
```

---

## Phase 4: Topbar global + error boundaries

Sidebar уже в хорошем состоянии (PRIMARY + SECONDARY группы, CTA, user-card). Что отсутствует — единый topbar с breadcrumbs + ⌘K + bell + user-menu, **и** error boundaries вообще на всём сайте.

**Files:**
- Create: `web/src/components/global-topbar.tsx`, `web/src/components/global-topbar.test.tsx`
- Create: `web/src/components/command-palette.tsx`
- Create: `web/src/app/error.tsx`, `web/src/app/(bank)/error.tsx`, `web/src/app/(accountant)/error.tsx`, `web/src/app/not-found.tsx`
- Modify: `web/src/components/app-shell.tsx`

---

### Task 4.1: Add root error boundary

- [ ] **Step 4.1.1: Create `web/src/app/error.tsx`**

```tsx
"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // TODO[CA-064]: ship к real observability (Sentry/posthog) когда подключим.
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg)] p-6">
      <div className="max-w-md rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h1 className="text-[18px] font-semibold text-[var(--ink-1)]">
          Что-то пошло не так
        </h1>
        <p className="mt-2 text-[13.5px] text-[var(--ink-3)]">
          Произошла непредвиденная ошибка. Попробуй обновить страницу. Если
          ошибка повторяется — сообщи в support с кодом{" "}
          <code className="font-mono text-[12px]">{error.digest ?? "—"}</code>.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-[var(--brand-primary-hover)]"
        >
          Попробовать снова
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4.1.2: Create `web/src/app/(bank)/error.tsx` and `web/src/app/(accountant)/error.tsx`**

Оба файла идентичны root `error.tsx` (с тем же текстом). Cause: Next.js не делегирует route-group ошибку в root error.tsx, нужны explicit per-segment.

- [ ] **Step 4.1.3: Create `web/src/app/not-found.tsx`**

```tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg)] p-6">
      <div className="max-w-md rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h1 className="text-[18px] font-semibold text-[var(--ink-1)]">
          Страница не найдена
        </h1>
        <p className="mt-2 text-[13.5px] text-[var(--ink-3)]">
          Возможно, она была перемещена или удалена.
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-[var(--brand-primary-hover)]"
        >
          На главную
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 4.1.4: Verify**

```powershell
cd web && npm run build
```
Expected: build succeeds.

Manual smoke (запусти `npm run dev`):
1. Открой `http://localhost:3000/nonexistent-page` → должна показаться «Страница не найдена».
2. Открой компонент с искусственно брошенной ошибкой (можно временно добавить `throw new Error("boom")` в `dossier-view.tsx`) → error.tsx должен показаться. Удали throw.

- [ ] **Step 4.1.5: Commit**

```powershell
git add web/src/app/error.tsx web/src/app/\(bank\)/error.tsx web/src/app/\(accountant\)/error.tsx web/src/app/not-found.tsx
git commit -m "feat(web): error.tsx + not-found.tsx на всех уровнях"
```

### Task 4.2: Global topbar component

В manual-input уже есть свой `web/src/components/topbar.tsx` — он специализированный (breadcrumbs + draft indicator). Создадим `global-topbar.tsx` отдельно — universal, поверх всех bank/accountant маршрутов, с ⌘K и bell. Specialized topbar в manual-input остаётся как есть (он dedicated для формы).

- [ ] **Step 4.2.1: Write topbar test**

Create `web/src/components/global-topbar.test.tsx`:

```tsx
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { GlobalTopbar } from "./global-topbar";

afterEach(cleanup);

describe("GlobalTopbar", () => {
  it("renders breadcrumbs", () => {
    render(<GlobalTopbar crumbs={[{ label: "Поиск", href: "/search" }, { label: "ИНН 201308534", current: true }]} />);
    expect(screen.getByText("Поиск")).toBeTruthy();
    expect(screen.getByText("ИНН 201308534")).toBeTruthy();
  });

  it("opens command palette on Cmd+K", () => {
    const onSearchOpen = vi.fn();
    render(<GlobalTopbar crumbs={[]} onSearchOpen={onSearchOpen} />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(onSearchOpen).toHaveBeenCalled();
  });
});
```

- [ ] **Step 4.2.2: Run, verify FAIL**

- [ ] **Step 4.2.3: Implement `web/src/components/global-topbar.tsx`**

```tsx
"use client";

import { Bell, ChevronRight, Search, HelpCircle } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

export type Crumb = { label: string; href?: string; current?: boolean };

export function GlobalTopbar({
  crumbs,
  onSearchOpen,
}: {
  crumbs: Crumb[];
  onSearchOpen?: () => void;
}) {
  useEffect(() => {
    if (!onSearchOpen) return;
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onSearchOpen!();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onSearchOpen]);

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-6">
      <nav aria-label="Хлебные крошки" className="flex min-w-0 items-center gap-1.5 text-[13px]">
        {crumbs.map((c, i) => (
          <span key={i} className="flex items-center gap-1.5 min-w-0">
            {i > 0 && <ChevronRight className="size-3.5 text-[var(--ink-4)]" aria-hidden />}
            {c.href && !c.current ? (
              <Link href={c.href} className="truncate text-[var(--ink-3)] hover:text-[var(--ink-1)]">
                {c.label}
              </Link>
            ) : (
              <span className={c.current ? "truncate font-medium text-[var(--ink-1)]" : "truncate text-[var(--ink-3)]"}>
                {c.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          onClick={onSearchOpen}
          className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-[12.5px] text-[var(--ink-3)] hover:border-[var(--border-strong)]"
        >
          <Search className="size-3.5" />
          <span>Поиск</span>
          <kbd className="ml-2 rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 py-px font-mono text-[10px] text-[var(--ink-4)]">⌘K</kbd>
        </button>
        <Link
          href="/help"
          aria-label="Помощь"
          className="grid size-9 place-items-center rounded-md text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          <HelpCircle className="size-4" />
        </Link>
        <button
          type="button"
          aria-label="Уведомления"
          className="grid size-9 place-items-center rounded-md text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          <Bell className="size-4" />
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 4.2.4: Run, verify PASS**

`cd web && npx vitest run src/components/global-topbar.test.tsx`
Expected: 2 passed.

- [ ] **Step 4.2.5: Commit**

```powershell
git add web/src/components/global-topbar.tsx web/src/components/global-topbar.test.tsx
git commit -m "feat(web): GlobalTopbar с breadcrumbs + ⌘K trigger + bell"
```

### Task 4.3: Command palette skeleton

- [ ] **Step 4.3.1: Implement `web/src/components/command-palette.tsx`**

```tsx
"use client";

import { Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type Item = { label: string; href: string; section: string };

const ITEMS: Item[] = [
  { label: "Поиск заёмщика", href: "/search", section: "Навигация" },
  { label: "История досье", href: "/history", section: "Навигация" },
  { label: "Новая заявка", href: "/manual-input", section: "Действия" },
  { label: "Настройки", href: "/settings", section: "Навигация" },
  { label: "Помощь", href: "/help", section: "Навигация" },
];

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      setQuery("");
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const filtered = ITEMS.filter((i) =>
    i.label.toLowerCase().includes(query.toLowerCase()),
  );
  const grouped = filtered.reduce<Record<string, Item[]>>((acc, item) => {
    (acc[item.section] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-start pt-[10vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Командная палитра"
    >
      <button
        type="button"
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />
      <div className="relative z-10 w-full max-w-[600px] rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-xl mx-auto">
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-3">
          <Search className="size-4 text-[var(--ink-4)]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Найти страницу или действие…"
            className="flex-1 bg-transparent text-[14px] text-[var(--ink-1)] placeholder-[var(--ink-4)] focus:outline-none"
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="text-[var(--ink-4)] hover:text-[var(--ink-1)]"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="max-h-[400px] overflow-y-auto p-2">
          {Object.entries(grouped).length === 0 ? (
            <div className="px-3 py-6 text-center text-[13px] text-[var(--ink-3)]">
              Ничего не найдено
            </div>
          ) : (
            Object.entries(grouped).map(([section, items]) => (
              <div key={section} className="mb-2">
                <div className="px-2 pb-1 text-[10.5px] font-semibold tracking-[0.1em] text-[var(--ink-4)] uppercase">
                  {section}
                </div>
                {items.map((item) => (
                  <button
                    key={item.href}
                    type="button"
                    onClick={() => {
                      router.push(item.href);
                      onClose();
                    }}
                    className="block w-full rounded-md px-3 py-2 text-left text-[13.5px] text-[var(--ink-1)] hover:bg-[var(--surface-2)]"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4.3.2: Commit**

```powershell
git add web/src/components/command-palette.tsx
git commit -m "feat(web): CommandPalette (⌘K) skeleton — навигация + действия"
```

### Task 4.4: Wire topbar + palette в AppShell

- [ ] **Step 4.4.1: Modify `web/src/components/app-shell.tsx`**

Замени тело файла:

```tsx
"use client";

import { type ReactNode, useState } from "react";
import { usePathname } from "next/navigation";

import { BankSidebar } from "@/app/(bank)/_components/sidebar";
import { Sidebar as AccountantSidebar } from "@/app/(accountant)/_components/sidebar";
import { useAppMode } from "@/lib/use-app-mode";
import { GlobalTopbar, type Crumb } from "@/components/global-topbar";
import { CommandPalette } from "@/components/command-palette";

function deriveCrumbs(pathname: string): Crumb[] {
  // Минимальный mapping; будет расширяться по мере добавления страниц.
  // Manual-input страница имеет собственный Topbar — там derived crumbs
  // приходят из step state, GlobalTopbar там пропускается через showTopbar prop.
  if (pathname.startsWith("/search")) return [{ label: "Поиск заёмщика", current: true }];
  if (pathname.startsWith("/history")) return [{ label: "История досье", current: true }];
  if (pathname.startsWith("/dossier/")) {
    return [
      { label: "История", href: "/history" },
      { label: "Досье", current: true },
    ];
  }
  if (pathname.startsWith("/settings")) return [{ label: "Настройки", current: true }];
  if (pathname.startsWith("/help")) return [{ label: "Помощь", current: true }];
  return [];
}

export function AppShell({
  children,
  showTopbar = true,
}: {
  children: ReactNode;
  showTopbar?: boolean;
}) {
  const mode = useAppMode();
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const SidebarComponent = mode === "bank" ? BankSidebar : AccountantSidebar;
  const crumbs = deriveCrumbs(pathname);

  return (
    <div className="grid min-h-screen grid-cols-[260px_minmax(0,1fr)] bg-[var(--bg)]">
      <SidebarComponent />
      <main className="flex min-w-0 flex-col">
        {showTopbar && <GlobalTopbar crumbs={crumbs} onSearchOpen={() => setPaletteOpen(true)} />}
        <div className="flex-1">{children}</div>
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      </main>
    </div>
  );
}
```

- [ ] **Step 4.4.2: Pass `showTopbar={false}` для manual-input layout**

Manual-input уже использует свой `Topbar` внутри view. В layout `/manual-input` (если есть) пробрось `showTopbar={false}` в AppShell. Если AppShell не вызывается напрямую в `/manual-input/layout.tsx` — найди где он вызывается и адаптируй.

- [ ] **Step 4.4.3: Verify**

```powershell
cd web
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

Manual smoke:
1. `npm run dev`
2. `/search` → должны быть breadcrumbs «Поиск заёмщика», ⌘K кнопка, bell.
3. `Cmd+K` (или `Ctrl+K`) → командная палитра с 5 пунктами.
4. Esc → закрывается.

- [ ] **Step 4.4.4: Commit**

```powershell
git add web/src/components/app-shell.tsx
git commit -m "feat(web): GlobalTopbar + CommandPalette wired в AppShell"
```

---

## Phase 5: KPI / manual-input polish

JetBrains Mono для чисел в KPI cards уже частично есть (см. `score-gauge.tsx:74` — `font-mono text-[56px]`). Цель — расширить на все KPI/financial значения, добавить auto-save pulse-dot, inline helpers, убрать fabricated «норма для отрасли» если она реально присутствует.

**Files:**
- Modify: `web/src/features/dossier/kpi-card.tsx`, `web/src/features/dossier/kpi-row.tsx`
- Modify: `web/src/components/topbar.tsx` (manual-input topbar — добавить pulse-dot)
- Modify: `web/src/features/manual-input/components/step-1-borrower.tsx` (inline helper: срок деятельности)
- Audit: `web/src/features/manual-input/components/step-2-financials.tsx` (поиск «норма для отрасли»)

---

### Task 5.1: JetBrains Mono на всех числах в KPI

- [ ] **Step 5.1.1: Read `web/src/features/dossier/kpi-card.tsx` и `kpi-row.tsx`**

- [ ] **Step 5.1.2: Apply `font-mono` на числовые значения**

Найди все места где рендерится число (revenue, profit, ROE %, Debt/EBIT, scores) и добавь `font-mono` если его нет. Используй `tabular-nums` если column-выравнивание нужно: `font-mono tabular-nums`.

- [ ] **Step 5.1.3: Verify visually**

`npm run dev`, открой dossier → числа в моно-шрифте.

- [ ] **Step 5.1.4: Commit**

```powershell
git add web/src/features/dossier/kpi-card.tsx web/src/features/dossier/kpi-row.tsx
git commit -m "feat(web): JetBrains Mono на числовых значениях в KPI"
```

### Task 5.2: Auto-save pulse-dot в manual-input Topbar

`web/src/components/topbar.tsx` (manual-input topbar) показывает draft state. Добавляем pulsing dot когда `state === "saving"`.

- [ ] **Step 5.2.1: Read current `web/src/components/topbar.tsx`**

- [ ] **Step 5.2.2: Add pulse animation в `globals.css` (если ещё нет)**

В `web/src/app/globals.css` в `@layer base` добавь:

```css
@layer base {
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.85); }
  }
  .pulse-dot {
    animation: pulse-dot 1.4s ease-in-out infinite;
  }
}
```

- [ ] **Step 5.2.3: Apply в topbar**

В draft-indicator секции `topbar.tsx` (где `state === "saving"`):

```tsx
{state === "saving" && (
  <span className="flex items-center gap-1.5 text-[12px] text-[var(--ink-3)]">
    <span className="size-1.5 rounded-full bg-[var(--brand-primary)] pulse-dot" />
    Сохраняем черновик…
  </span>
)}
{state === "saved" && at && (
  <span className="flex items-center gap-1.5 text-[12px] text-[var(--ink-3)]">
    <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
    Черновик сохранён · {formatTime(at)}
  </span>
)}
```

- [ ] **Step 5.2.4: Verify в браузере**

`npm run dev`, открой `/manual-input`, заполни Шаг 1, кликни «Далее» → dot должен пульсировать пока идёт save.

- [ ] **Step 5.2.5: Commit**

```powershell
git add web/src/app/globals.css web/src/components/topbar.tsx
git commit -m "feat(web): pulse-dot для draft-save indicator"
```

### Task 5.3: Inline helper «срок деятельности» под registrationDate

- [ ] **Step 5.3.1: Helper function with TDD**

Create `web/src/features/manual-input/lib/duration.ts`:

```typescript
export function formatBusinessAge(
  registrationDate: string,
  now: Date = new Date(),
): string | null {
  if (!registrationDate || !/^\d{4}-\d{2}-\d{2}$/.test(registrationDate)) return null;
  const reg = new Date(registrationDate);
  if (Number.isNaN(reg.getTime())) return null;
  if (reg > now) return null;

  let years = now.getFullYear() - reg.getFullYear();
  let months = now.getMonth() - reg.getMonth();
  if (now.getDate() < reg.getDate()) months -= 1;
  if (months < 0) {
    years -= 1;
    months += 12;
  }

  const yLabel = years === 1 ? "год" : years >= 2 && years <= 4 ? "года" : "лет";
  const mLabel = months === 1 ? "мес" : "мес"; // короткая форма для inline
  if (years === 0) return `${months} ${mLabel}`;
  if (months === 0) return `${years} ${yLabel}`;
  return `${years} ${yLabel} ${months} ${mLabel}`;
}
```

Create `web/src/features/manual-input/lib/duration.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { formatBusinessAge } from "./duration";

describe("formatBusinessAge", () => {
  const now = new Date("2026-05-13");

  it("returns years + months", () => {
    expect(formatBusinessAge("2017-04-12", now)).toBe("9 лет 1 мес");
  });
  it("handles 1-year edge case", () => {
    expect(formatBusinessAge("2025-05-13", now)).toBe("1 год");
  });
  it("returns null for invalid date", () => {
    expect(formatBusinessAge("abc", now)).toBeNull();
  });
  it("returns null for future date", () => {
    expect(formatBusinessAge("2030-01-01", now)).toBeNull();
  });
  it("returns just months when <1 year", () => {
    expect(formatBusinessAge("2026-01-13", now)).toBe("4 мес");
  });
});
```

- [ ] **Step 5.3.2: Run test, verify PASS**

`cd web && npx vitest run src/features/manual-input/lib/duration.test.ts`
Expected: 5 passed.

- [ ] **Step 5.3.3: Wire в step-1-borrower.tsx**

Найди поле `registrationDate` в `step-1-borrower.tsx`. Под input'ом добавь:

```tsx
import { formatBusinessAge } from "../lib/duration";

// inside component, where registrationDate is watched:
const registrationDate = watch("step1.registrationDate");
const businessAge = formatBusinessAge(registrationDate);

// ...под input:
{businessAge && (
  <p className="mt-1 text-[12px] text-[var(--ink-3)]">
    Срок деятельности: <span className="font-medium text-[var(--ink-2)]">{businessAge}</span>
  </p>
)}
```

И аналогичный helper «9 цифр · формат ГНК» под `inn`:

```tsx
{inn && /^\d{9}$/.test(inn) && (
  <p className="mt-1 text-[12px] text-[var(--state-ok-fg)]">9 цифр · формат ГНК</p>
)}
{inn && inn.length > 0 && inn.length < 9 && (
  <p className="mt-1 text-[12px] text-[var(--ink-3)]">{`Введено ${inn.length} из 9 цифр`}</p>
)}
```

- [ ] **Step 5.3.4: Verify**

`npm run dev`, заполни Шаг 1 c registrationDate = `2017-04-12` → должно показать «9 лет 1 мес».

- [ ] **Step 5.3.5: Commit**

```powershell
git add web/src/features/manual-input
git commit -m "feat(web): inline helpers — срок деятельности + ИНН-формат под полями Шага 1"
```

### Task 5.4: Audit «норма для отрасли»

- [ ] **Step 5.4.1: Search**

```powershell
cd web
git grep -n "норма для отрасли\|норма отрасли\|0\\.55\|0\\.46" src/features
```

Если найдены строки с fabricated industry benchmark — переходи к 5.4.2. Если нет — задача завершена, skip 5.4.2/5.4.3, commit пропусти.

- [ ] **Step 5.4.2: Remove industry-norm tag**

Удали JSX элемент показывающий «норма для отрасли ≤ X». Оставь только сырой коэффициент.

В замену — короткий tooltip с источником если есть подтверждённый source (ЦБ-постановление, Базель). Иначе — просто числовое значение без оценки.

- [ ] **Step 5.4.3: Commit (если правки были)**

```powershell
git add web/src/features
git commit -m "fix(web): убран fabricated «норма для отрасли» бенчмарк без source"
```

---

## Phase 6: Bank Mode login redesign

Сейчас `/login` (если есть) — на базе semantic токенов после Phase 1. Цель — дать тёмный navy gradient background + JetBrains Mono для email/password + footer с TLS-сигналом «Безопасное соединение».

**Files:**
- Modify: `web/src/app/login/page.tsx` (или `web/src/app/(bank)/login/page.tsx` — найди по факту)

---

### Task 6.1: Login redesign

- [ ] **Step 6.1.1: Find login route**

```powershell
cd web
git grep -nl "login" src/app | Where-Object { $_ -match "page\.tsx$" }
```

- [ ] **Step 6.1.2: Apply dark navy gradient + mono inputs**

Внеси изменения в JSX login страницы:

```tsx
// Background:
<div className="grid min-h-screen place-items-center bg-gradient-to-br from-[var(--nav-bg)] via-[var(--nav-bg-2)] to-[var(--nav-bg)] p-6">

// Card:
<div className="w-full max-w-[420px] rounded-xl border border-[var(--nav-border)] bg-[rgba(15,23,42,0.55)] p-8 backdrop-blur-sm shadow-2xl">

// Heading:
<div className="mb-6 text-center">
  <div className="text-[10.5px] font-semibold tracking-[0.2em] text-[var(--nav-text-3)] uppercase">
    Authentication
  </div>
  <h1 className="mt-2 text-[22px] font-semibold text-white">Вход в систему</h1>
  <p className="mt-1 text-[13px] text-[var(--nav-text-2)]">Кредитный аналитик</p>
</div>

// Inputs:
<input
  type="email"
  className="w-full rounded-md border border-[var(--nav-border)] bg-[rgba(11,18,32,0.6)] px-3 py-2.5 font-mono text-[13.5px] text-white placeholder-[var(--nav-text-3)] focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary-ring)]"
  placeholder="analyst@bank.uz"
/>

// TLS footer:
<div className="mt-6 flex items-center justify-center gap-1.5 text-[11px] text-[var(--nav-text-3)]">
  <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
  Безопасное соединение · TLS 1.3
</div>
```

- [ ] **Step 6.1.3: Verify accessibility contrast**

Запусти axe-core или manual check: `--nav-text-2` (`#94A3B8`) на `--nav-bg` (`#0B1220`) → contrast ratio ≥ 4.5:1 для AA. Если не проходит — поднимай к `--nav-text` (`#E2E8F0`).

```powershell
# Можно использовать https://webaim.org/resources/contrastchecker/ вручную
# или установить axe-cli локально для CI smoke
```

- [ ] **Step 6.1.4: Commit**

```powershell
git add web/src/app
git commit -m "feat(web): Bank Mode login — dark navy gradient + JetBrains Mono + TLS signal"
```

---

## Phase 7: Demo seed script

Backend утилита: 3 готовых borrower'а с realistic UZ MSB-паттерном для демонстраций. Закрывает «ЙЦУЙЦУЙЦУ» риск.

**Files:**
- Create: `scripts/seed_demo_borrowers.py`
- Create: `tests/scripts/seed_demo_borrowers_test.py`

---

### Task 7.1: Seed script с realistic patterns

- [ ] **Step 7.1.1: Write failing test**

Create `tests/scripts/seed_demo_borrowers_test.py`:

```python
"""Smoke test for demo seed script."""
from __future__ import annotations

from decimal import Decimal

import pytest

from scripts.seed_demo_borrowers import build_demo_borrowers


def test_returns_three_demo_borrowers() -> None:
    borrowers = build_demo_borrowers()
    assert len(borrowers) == 3
    inns = {b["inn"] for b in borrowers}
    assert len(inns) == 3, "ИНН должны быть уникальными"


def test_each_has_realistic_quarterly_revenue() -> None:
    borrowers = build_demo_borrowers()
    for b in borrowers:
        revenue = b["quarterly_revenue"]
        assert len(revenue) == 8, "8 кварталов (2 года)"
        # Никакой ровный quarter-over-quarter рост: коэффициент вариации >= 0.05
        values = [float(v) for v in revenue]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        cv = std / mean if mean > 0 else 0
        assert cv >= 0.05, f"Слишком ровная выручка (cv={cv:.3f}) — добавь сезонность"


def test_retail_has_q4_peak() -> None:
    borrowers = build_demo_borrowers()
    retail = next(b for b in borrowers if b["industry"] == "retail")
    quarterly = retail["quarterly_revenue"]
    # 4-й и 8-й (Q4 каждого года) — наибольшие
    q1, q2, q3, q4, q5, q6, q7, q8 = quarterly
    assert q4 > q1 and q4 > q2 and q4 > q3
    assert q8 > q5 and q8 > q6 and q8 > q7


def test_agro_has_q2_q3_peak() -> None:
    borrowers = build_demo_borrowers()
    agro = next(b for b in borrowers if b["industry"] == "agro")
    quarterly = agro["quarterly_revenue"]
    q1, q2, q3, q4, q5, q6, q7, q8 = quarterly
    peak = max(q2, q3)
    assert peak > q1 and peak > q4
```

- [ ] **Step 7.1.2: Run test, verify FAIL**

```powershell
uv run pytest tests/scripts/seed_demo_borrowers_test.py -v
```
Expected: FAIL (import error).

- [ ] **Step 7.1.3: Implement `scripts/seed_demo_borrowers.py`**

```python
"""
Demo seed: 3 realistic UZ MSB borrowers с сезонностью.

Usage:
    uv run python -m scripts.seed_demo_borrowers --commit

Без --commit печатает JSON, не пишет в БД.

Industries:
- retail   — потребительская розница, Q4 пик (новогодние закупки)
- agro     — сельхозпроизводитель, Q2-Q3 пик (сезон уборки/переработки)
- services — B2B-услуги, ровный профиль с лёгким YoY-ростом
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from typing import Any

# Базовые годовые выручки (сум), будут разбиты по кварталам с сезонностью.
DEMO_BORROWERS: list[dict[str, Any]] = [
    {
        "inn": "301234567",
        "name": "ООО «Зумрад-Текстиль»",
        "industry": "retail",
        "legal_form": "LLC",
        "registration_date": "2017-04-12",
        "okved_main": "47.51",
        "director_name": "Каримов Шохрух Анварович",
        "director_appointed_at": "2021-02-15",
        "registered_address": "г. Ташкент, Юнусабадский р-н, ул. Мустакиллик, 41",
        "annual_revenue_base": Decimal("3200000000"),  # 3.2 млрд сум
        "seasonality": [0.9, 1.0, 1.1, 1.4, 1.0, 1.1, 1.2, 1.5],  # 8 кв
    },
    {
        "inn": "402345678",
        "name": "ФХ «Хосилот-Агро»",
        "industry": "agro",
        "legal_form": "FARM",
        "registration_date": "2014-09-03",
        "okved_main": "01.13",
        "director_name": "Юлдашев Бахром Тошпулатович",
        "director_appointed_at": "2018-06-01",
        "registered_address": "Ферганская обл., Бувайдинский р-н, с. Сартепа",
        "annual_revenue_base": Decimal("1800000000"),
        "seasonality": [0.7, 1.5, 1.3, 0.8, 0.7, 1.6, 1.3, 0.9],
    },
    {
        "inn": "503456789",
        "name": "ООО «ТехноСервис Плюс»",
        "industry": "services",
        "legal_form": "LLC",
        "registration_date": "2019-11-20",
        "okved_main": "62.02",
        "director_name": "Рахимов Жасур Алишерович",
        "director_appointed_at": "2023-08-10",
        "registered_address": "г. Самарканд, ул. Регистан, 12",
        "annual_revenue_base": Decimal("950000000"),
        "seasonality": [0.95, 1.05, 0.98, 1.02, 1.00, 1.08, 1.04, 1.10],
    },
]


def build_demo_borrowers() -> list[dict[str, Any]]:
    """Возвращает 3 borrower-record'а с quarterly_revenue."""
    result: list[dict[str, Any]] = []
    for spec in DEMO_BORROWERS:
        quarterly_base = spec["annual_revenue_base"] / Decimal(4)
        quarterly = [
            quarterly_base * Decimal(str(coef)) for coef in spec["seasonality"]
        ]
        record = {k: v for k, v in spec.items() if k not in ("annual_revenue_base", "seasonality")}
        record["quarterly_revenue"] = quarterly
        result.append(record)
    return result


def _serialize(borrowers: list[dict[str, Any]]) -> str:
    return json.dumps(
        borrowers,
        ensure_ascii=False,
        indent=2,
        default=lambda v: str(v) if isinstance(v, Decimal) else v,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Записать в БД")
    args = parser.parse_args()
    borrowers = build_demo_borrowers()
    if args.commit:
        # TODO[CA-065]: write to repository (требует DI session). Пока — печать.
        raise NotImplementedError("--commit не реализован; пользуйся stdout для inspection")
    print(_serialize(borrowers))


if __name__ == "__main__":
    main()
```

- [ ] **Step 7.1.4: Run test, verify PASS**

```powershell
uv run pytest tests/scripts/seed_demo_borrowers_test.py -v
```
Expected: 4 passed.

- [ ] **Step 7.1.5: Smoke run**

```powershell
uv run python -m scripts.seed_demo_borrowers
```

Expected: JSON 3 borrowers с реалистичными ИНН (3019/4023/5034), сезонностью в quarterly_revenue.

- [ ] **Step 7.1.6: Commit**

```powershell
git add scripts/seed_demo_borrowers.py tests/scripts
git commit -m "feat(scripts): demo seed — 3 realistic UZ MSB borrowers с сезонностью"
```

---

## Phase 8: Quarterly tables audit + add if missing

Step 2 (`step-2-financials.tsx`) — нужно убедиться что отображение Q1/Q2/Q3/Q4 + ИТОГО ЗА ГОД присутствует. Текущая структура содержит `financial-table.tsx` — посмотреть какая.

**Files:**
- Audit: `web/src/features/manual-input/components/financial-table.tsx`, `web/src/features/manual-input/components/step-2-financials.tsx`
- Possibly Create: `web/src/features/manual-input/components/quarterly-table.tsx` + test

---

### Task 8.1: Audit current implementation

- [ ] **Step 8.1.1: Read both files**

`Read web/src/features/manual-input/components/financial-table.tsx`
`Read web/src/features/manual-input/components/step-2-financials.tsx`

- [ ] **Step 8.1.2: Decide path**

- **Если уже есть Q1/Q2/Q3/Q4 + total + CAGR**: skip Phase 8 entirely, commit пропусти.
- **Если есть только годовой ввод (current_year / prior_year)**: добавить quarterly слой — Task 8.2.
- **Если есть quarterly но без CAGR row**: Task 8.3 — добавить row.

### Task 8.2: (Conditional) Add quarterly table

Если не хватает quarterly:

- [ ] **Step 8.2.1: Define schema extension**

Расширь `web/src/features/manual-input/schema.ts` (поле `step2.quarterlyRevenue: z.array(...).length(8).optional()`).

- [ ] **Step 8.2.2: Render table в step-2-financials.tsx**

(Полный код опускаю — он зависит от текущего layout, который engineer прочитает на 8.1.1. Дизайн: 4 столбца с поквартальными значениями + 5-й «ИТОГО» + computed CAGR row.)

- [ ] **Step 8.2.3: Add backend ingestion**

Расширь `application/dto/manual_input.py` (Pydantic `Step2Input`) — `quarterly_revenue: list[Money] | None` optional. **НЕ ломай существующий контракт** — поле опциональное.

- [ ] **Step 8.2.4: Verify**

```powershell
cd web && npm run lint && npx tsc --noEmit && npm run test:run && npm run build
uv run pytest -q
```

- [ ] **Step 8.2.5: Commit**

```powershell
git add web/src/features/manual-input src/application
git commit -m "feat(manual-input): quarterly revenue table + CAGR row в Step 2"
```

---

## Phase 9: i18n keys naming (CA-063) — отложено до закрытия 4

Расширения keyspace + mode-prefix. Этот раздел оставлен умышленно высокоуровневым: после Phase 4 engineer должен принять решение «подключаем узбекский сейчас или потом».

**Files:**
- Create: `web/src/i18n/ru.json`, `web/src/i18n/uz.json` (если узбекский)
- Create: `web/src/lib/i18n.ts` (next-intl provider)
- Sweep: все JSX-strings русские → keys

### Task 9.1: Install next-intl

```powershell
cd web && npm install next-intl
```

### Task 9.2: Build keyspace

Структура:
```json
{
  "shared": { "cta": { "save": "Сохранить", "cancel": "Отмена" } },
  "bank": {
    "borrower": { "title": "Заёмщик" },
    "cta": { "new_application": "Новая заявка" }
  },
  "accountant": {
    "my_company": { "title": "Моя фирма" },
    "cta": { "upload_files": "Загрузить файлы" }
  }
}
```

### Task 9.3: Provider в layout

В `web/src/app/layout.tsx`:

```tsx
import { NextIntlClientProvider } from "next-intl";
import messages from "../i18n/ru.json";

// inside RootLayout:
<NextIntlClientProvider messages={messages} locale="ru">
  {children}
</NextIntlClientProvider>
```

### Task 9.4: Sweep hardcoded strings

Это большой sweep по features/. Engineer должен делать по одной feature за раз, с commit'ом на каждую. Это не plan-failure («repeat code») — это явное указание паттерна, который повторяется ~50 раз и не поддаётся атомарной декомпозиции в плане.

### Task 9.5: Verify

```powershell
cd web && npm run lint && npx tsc --noEmit && npm run test:run && npm run build
```

---

## Self-Review Checklist

После завершения всех фаз — пройти checklist:

- [ ] **ADR-0011 закоммичен** (Phase 0)
- [ ] **`var(--ca-*)` и `var(--ub-*)` отсутствуют в `web/src/`** (`git grep` пустой)
- [ ] **ESLint blocks hardcoded hex в features/components** (canary test gone, rule passes)
- [ ] **`APP_MODE` / `useAppMode()` только в shells** (`git grep` в features/components пустой)
- [ ] **`app/error.tsx` + per-segment error boundaries присутствуют**
- [ ] **`Cmd+K` открывает командную палитру**
- [ ] **JetBrains Mono активен для числовых KPI**
- [ ] **Pulse-dot при save**
- [ ] **«Срок деятельности» inline-helper рендерится корректно для valid date**
- [ ] **Login — dark gradient + TLS-signal**
- [ ] **`scripts/seed_demo_borrowers.py` smoke-runs**
- [ ] **Все verify-gates зелёные:** `npm run lint && npx tsc --noEmit && npm run test:run && npm run build` + `uv run pytest -q`

## Out-of-scope (не делать в этом плане)

- PDF redesign — отдельный design language, отдельный план.
- Mobile responsive — банкир десктопный.
- Кастомные animations кроме pulse-dot.
- Замена `score-gauge.tsx` (полудуга со стрелкой) на DSCR ring style — действующий gauge уже хорошо сделан (см. `score-gauge.tsx` — цветные сектора + needle + recommendation pill). Если позже захочется DSCR-ring style — отдельный спec.
- Fabricated «норма для отрасли» — если её нет в коде (см. Task 5.4) — не добавлять.
- Real ГНК-лукап (TODO[CA-003]).
- Refresh-token rotation (TODO[CA-019]).

## Execution recommendation

В новой сессии открыть этот файл и стартовать через `superpowers:executing-plans` skill. Идти строго по фазам, каждую фазу закрывать verify-gate'ом перед следующей. Если engineer наткнётся на conflict с PROJECT_BRIEF / ADR — стоп, спросить пользователя, не угадывать.
