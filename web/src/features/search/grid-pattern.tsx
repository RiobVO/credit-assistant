// Phase 2 (DS-PHASE-2): фоновый pattern 40×40 квадратов под ambient orb'ами.
// Виден только в центре экрана через radial mask — по краям растворяется.
// Стили в `globals.css` (`.ds-grid-pattern`).
// Phase 3 (DS-PHASE-3): `tone="brand"` — brand-primary tint для /history.
export function GridPattern({ tone = "default" }: { tone?: "default" | "brand" }) {
  const cls =
    tone === "brand"
      ? "ds-grid-pattern ds-grid-pattern--brand"
      : "ds-grid-pattern";
  return <div className={cls} aria-hidden />;
}
