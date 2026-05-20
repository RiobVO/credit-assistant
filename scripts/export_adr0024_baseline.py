"""ADR-0024 regression baseline export.

Дампит для 5 demo dossier (BR-2026-0030, 0040, 0042, 0046, 0047) поля
case_id / score / recommendation / severity_breakdown / red_flag rule_id+severity
/ rules_evaluated. Output → `tests/fixtures/regression/adr0024_baseline.json`.

Используется как baseline для Session-1 KPI calculator extension — после A+B+C
дампим повторно в `adr0024_post.json` (gitignored) и diff'ом смотрим, что
добавились только KPI поля в payload, а score не сдвинулся >5 пунктов.

Usage:
    docker compose exec api bash -c "cd /app && PYTHONPATH=/app:/app/src \\
        uv run --no-sync python -m scripts.export_adr0024_baseline"
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

from infrastructure.persistence.database import dispose_engine, get_session_factory
from infrastructure.persistence.models.dossier import DossierORM

DEMO_CASE_IDS: tuple[str, ...] = (
    "BR-2026-0030",
    "BR-2026-0040",
    "BR-2026-0042",
    "BR-2026-0046",
    "BR-2026-0047",
)

# scripts/ → ../tests/fixtures/regression
_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT_PATH = _REPO_ROOT / "tests" / "fixtures" / "regression" / "adr0024_baseline.json"


async def _export() -> list[dict[str, Any]]:
    factory = get_session_factory()
    rows: list[dict[str, Any]] = []
    async with factory() as session:
        stmt = select(DossierORM).where(DossierORM.case_id.in_(DEMO_CASE_IDS))
        result = (await session.execute(stmt)).scalars().all()
        # Sort by case_id для детерминированного diff'а.
        for orm in sorted(result, key=lambda d: d.case_id):
            rows.append(
                {
                    "case_id": orm.case_id,
                    "score": orm.score,
                    "recommendation": orm.recommendation,
                    "severity_breakdown": dict(orm.severity_breakdown),
                    "rules_evaluated": orm.rules_evaluated,
                    "rules_version": orm.rules_version,
                    # red_flags JSONB — оставляем только rule_id+severity для regression.
                    # Полный evidence шумит diff и не относится к KPI-сцепке.
                    "red_flags": sorted(
                        (
                            {"rule_id": f["rule_id"], "severity": f["severity"]}
                            for f in orm.red_flags
                        ),
                        key=lambda f: (f["severity"], f["rule_id"]),
                    ),
                }
            )
    return rows


def main() -> int:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _run() -> list[dict[str, Any]]:
        try:
            return await _export()
        finally:
            await dispose_engine()

    rows = asyncio.run(_run())
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} dossiers to {_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
