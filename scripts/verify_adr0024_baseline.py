"""ADR-0024 Session 3 regression verify.

Загружает 5 demo snapshots из БД, прогоняет их через current
RuleRegistry, дампит deterministic JSON в `--out PATH`. Используется
для cross-branch diff: запустить на main → pre.json, переключиться
на feat → post.json, `git diff --no-index pre.json post.json`.

Session 3 backward-compat invariant: новые правила (TAX_PENALTIES
material gate, SHELL_COMPANY IE exclude, SINGLE_SUPPLIER foreign
escalation, OKVED_CHANGED_12M owner gate, LOAN_TO_REVENUE secured-
variant) silent на 5 demo snapshots — все 5 новых полей имеют default
False / None в JSONB через `.get(..., default)`. Diff между main и
Session 3 должен быть пустым.

Usage:
    docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app:/app/src \\
        uv run --no-sync python -m scripts.verify_adr0024_baseline --out /tmp/replay.json"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from domain.entities.red_flag import RedFlag
from domain.services.scoring_service import RiskScore, ScoringService
from infrastructure.persistence.database import dispose_engine, get_session_factory
from infrastructure.persistence.mappers.borrower_mapper import borrower_from_orm
from infrastructure.persistence.mappers.snapshot_mapper import snapshot_from_payload
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.rules.registry_factory import load_registry

DEMO_CASE_IDS: tuple[str, ...] = (
    "BR-2026-0030",
    "BR-2026-0040",
    "BR-2026-0042",
    "BR-2026-0046",
    "BR-2026-0047",
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RULES_YAML = _REPO_ROOT / "config" / "rules" / "v1_uz_msb.yaml"


async def _replay() -> list[dict[str, object]]:
    """Replay 5 demo snapshots через current registry. Возвращает rows для JSON dump."""
    registry = load_registry(_RULES_YAML)
    scoring = ScoringService()
    factory = get_session_factory()
    rows: list[dict[str, object]] = []

    async with factory() as session:
        stmt = (
            select(DossierORM, BorrowerSnapshotORM, BorrowerORM)
            .join(BorrowerSnapshotORM, DossierORM.snapshot_id == BorrowerSnapshotORM.id)
            .join(BorrowerORM, BorrowerSnapshotORM.borrower_id == BorrowerORM.id)
            .where(DossierORM.case_id.in_(DEMO_CASE_IDS))
        )
        result = (await session.execute(stmt)).all()
        result_sorted = sorted(result, key=lambda r: r[0].case_id)

        for dossier, snapshot_orm, borrower_orm in result_sorted:
            borrower = borrower_from_orm(borrower_orm)
            snapshot = snapshot_from_payload(snapshot_orm.payload, borrower)

            flags: list[RedFlag] = registry.run_all(snapshot)
            score: RiskScore = scoring.score(flags, snapshot=snapshot)

            rows.append(
                {
                    "case_id": dossier.case_id,
                    "rules_evaluated": len(registry.rules),
                    "score": score.score,
                    "recommendation": score.recommendation.value,
                    "severity_breakdown": {
                        sev.value: cnt for sev, cnt in score.severity_breakdown.items()
                    },
                    "red_flags": sorted(
                        ({"rule_id": f.rule_id, "severity": f.severity.value} for f in flags),
                        key=lambda x: (x["severity"], x["rule_id"]),
                    ),
                }
            )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSON path для cross-branch diff.",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _run() -> list[dict[str, object]]:
        try:
            return await _replay()
        finally:
            await dispose_engine()

    rows = asyncio.run(_run())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote replay for {len(rows)} dossiers to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
