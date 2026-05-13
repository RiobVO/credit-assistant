// Phase 2 (DS-PHASE-2): фоновый pattern 40×40 квадратов под ambient orb'ами.
// Виден только в центре экрана через radial mask — по краям растворяется.
// Стили в `globals.css` (`.ds-grid-pattern`).
export function GridPattern() {
  return <div className="ds-grid-pattern" aria-hidden />;
}
