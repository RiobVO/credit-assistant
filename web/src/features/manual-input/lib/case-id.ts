// CA-DS18 Level 1: deterministic case_id из draft.id.
// Banking format `BR-YYYY-XXXX` (mirror PDF _format_application_id).
// XXXX = first 4 hex chars from draft UUID (без дефисов), uppercased.
// Стабильно между refresh/rerender; никаких Math.random.
//
// Level 2 (Postgres sequence через application entity) → CA-DS18b после
// Phase 4 application creation flow. Текущий format вытесняется когда
// backend начнёт отдавать real BR-2026-0042 sequence.

const HEX_PREFIX_LEN = 4;

export function formatCaseId(
  draftId: string | null,
  now: Date = new Date(),
): string | null {
  if (!draftId) return null;
  const hex = draftId.replace(/-/g, "").slice(0, HEX_PREFIX_LEN).toUpperCase();
  if (hex.length < HEX_PREFIX_LEN) return null;
  return `BR-${now.getFullYear()}-${hex}`;
}
