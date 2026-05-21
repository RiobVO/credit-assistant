"""Cleanup test data: убирает мусорные borrowers/analysts из БД перед demo.

Usage:
    # Сухой прогон — показать что будет удалено / переименовано, без записей в БД.
    docker compose exec api bash -c "cd /app/src && \\
        uv run --no-sync python -m scripts.cleanup_test_data --dry-run"

    # Боевой прогон — применить изменения (одна транзакция).
    docker compose exec api bash -c "cd /app/src && \\
        uv run --no-sync python -m scripts.cleanup_test_data --yes"

Что делает:

1. Удаляет borrower-rows с ``name`` ∈ ``BORROWER_BLACKLIST`` и каскадно:
   * связанные ``borrower_snapshots`` (FK RESTRICT — удаляем явно);
   * связанные ``dossiers`` (FK RESTRICT через snapshot).

2. Аналитики:
   * с ``full_name`` ∈ ``ANALYST_NAME_RENAMES`` — переименовываются (не удаляются),
     если row — единственный seeded analyst для login'а ``t04@bank.uz``.
     Это сохраняет seed для demo, но прячет «T0.4 Smoke» в bank-list.
   * с ``full_name`` ∈ ``ANALYST_BLACKLIST`` — удаляются **только если** на них
     не ссылается ни один dossier и audit_log (defensive — не теряем audit-trail).

Идемпотентен: повторный запуск ничего не удаляет (списки пустые → no-op).

Borrower.name — plain VARCHAR; Analyst.full_name — Fernet-encrypted через
``EncryptedString`` TypeDecorator: SQLAlchemy дешифрует на SELECT прозрачно.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.database import dispose_engine, get_session_factory
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.audit_log import AuditLogORM
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM

# Имена borrower'ов, которые мы хотим вычистить. Сравнение по полному ``name``
# (case-sensitive). Расширять список — только если он действительно мусор;
# реальные borrower'ы оставляем.
BORROWER_BLACKLIST: frozenset[str] = frozenset({
    "ЙЦУЙЦУЙЦУ",
    "TEST",
    "OOO Test T1.1",
})

# Аналитики, которых удаляем целиком (если на них нет dossier/audit-trail).
ANALYST_BLACKLIST: frozenset[str] = frozenset({
    "T1.1 Smoke Tester",
    "Smoke Тестер",
})

# Аналитики, которых **переименовываем** вместо удаления. Сохраняем login
# `t04@bank.uz` для pre-demo smoke, но прячем «Smoke» в bank-list /history.
ANALYST_NAME_RENAMES: dict[str, str] = {
    "T0.4 Smoke": "Demo Analyst",
}

# Email seeded-аналитика для demo — защищён от удаления независимо от
# совпадения по full_name.
PROTECTED_ANALYST_EMAILS: frozenset[str] = frozenset({"t04@bank.uz"})


async def _delete_borrowers(
    session: AsyncSession, dry_run: bool
) -> tuple[int, int, int]:
    """Возвращает (borrowers, snapshots, dossiers) — счётчики удалённых row'ов."""
    rows = (
        await session.execute(
            select(BorrowerORM.id, BorrowerORM.name).where(
                BorrowerORM.name.in_(BORROWER_BLACKLIST)
            )
        )
    ).all()
    if not rows:
        return 0, 0, 0

    borrower_ids = [r.id for r in rows]
    snapshot_ids = (
        await session.execute(
            select(BorrowerSnapshotORM.id).where(
                BorrowerSnapshotORM.borrower_id.in_(borrower_ids)
            )
        )
    ).scalars().all()

    dossier_count = 0
    if snapshot_ids:
        dossier_ids = (
            await session.execute(
                select(DossierORM.id).where(DossierORM.snapshot_id.in_(snapshot_ids))
            )
        ).scalars().all()
        dossier_count = len(dossier_ids)

    print("  Borrowers to delete:")
    for r in rows:
        print(f"    - {r.name!r} (id={r.id})")
    print(f"  Snapshots cascade: {len(snapshot_ids)}")
    print(f"  Dossiers cascade:  {dossier_count}")

    if dry_run:
        return len(rows), len(snapshot_ids), dossier_count

    # Каскад: dossiers → snapshots → borrowers. FK RESTRICT обязывает удалять
    # вручную в этом порядке.
    if snapshot_ids:
        await session.execute(
            delete(DossierORM).where(DossierORM.snapshot_id.in_(snapshot_ids))
        )
        await session.execute(
            delete(BorrowerSnapshotORM).where(BorrowerSnapshotORM.id.in_(snapshot_ids))
        )
    await session.execute(
        delete(BorrowerORM).where(BorrowerORM.id.in_(borrower_ids))
    )
    return len(rows), len(snapshot_ids), dossier_count


async def _rename_analysts(session: AsyncSession, dry_run: bool) -> int:
    """Переименовывает analyst.full_name согласно ANALYST_NAME_RENAMES."""
    if not ANALYST_NAME_RENAMES:
        return 0

    renamed = 0
    rows = (
        await session.execute(
            select(AnalystORM.id, AnalystORM.email, AnalystORM.full_name).where(
                AnalystORM.full_name.in_(tuple(ANALYST_NAME_RENAMES.keys()))
            )
        )
    ).all()
    for row in rows:
        new_name = ANALYST_NAME_RENAMES[row.full_name]
        print(f"  Rename analyst: {row.email} ({row.full_name!r} → {new_name!r})")
        if not dry_run:
            await session.execute(
                update(AnalystORM)
                .where(AnalystORM.id == row.id)
                .values(full_name=new_name)
            )
        renamed += 1
    return renamed


async def _delete_analysts(session: AsyncSession, dry_run: bool) -> int:
    """Удаляет analyst-row'ы из ANALYST_BLACKLIST, но только если на них нет
    ссылок из dossiers / audit_log. Никогда не трогает PROTECTED_ANALYST_EMAILS.
    """
    if not ANALYST_BLACKLIST:
        return 0

    rows = (
        await session.execute(
            select(AnalystORM.id, AnalystORM.email, AnalystORM.full_name).where(
                AnalystORM.full_name.in_(ANALYST_BLACKLIST)
            )
        )
    ).all()
    if not rows:
        return 0

    deleted = 0
    for row in rows:
        if row.email in PROTECTED_ANALYST_EMAILS:
            print(f"  Skip protected: {row.email} ({row.full_name!r})")
            continue

        ref_dossier = (
            await session.execute(
                select(DossierORM.id)
                .where(DossierORM.created_by_analyst_id == row.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        ref_audit = (
            await session.execute(
                select(AuditLogORM.id)
                .where(AuditLogORM.analyst_id == row.id)
                .limit(1)
            )
        ).scalar_one_or_none()

        if ref_dossier is not None or ref_audit is not None:
            reasons = []
            if ref_dossier is not None:
                reasons.append("dossier-trail")
            if ref_audit is not None:
                reasons.append("audit-log")
            print(
                f"  Skip (has references: {', '.join(reasons)}): "
                f"{row.email} ({row.full_name!r})"
            )
            continue

        print(f"  Delete analyst: {row.email} ({row.full_name!r})")
        if not dry_run:
            await session.execute(delete(AnalystORM).where(AnalystORM.id == row.id))
        deleted += 1
    return deleted


async def _run(dry_run: bool) -> int:
    factory = get_session_factory()
    async with factory() as session, session.begin():
        print(f"Mode: {'DRY-RUN' if dry_run else 'EXECUTE'}")
        print("--- Borrowers ---")
        b, s, d = await _delete_borrowers(session, dry_run)
        print("--- Analysts (rename) ---")
        r = await _rename_analysts(session, dry_run)
        print("--- Analysts (delete) ---")
        a = await _delete_analysts(session, dry_run)
        print()
        print(
            f"Summary: borrowers={b}, snapshots={s}, dossiers={d}, "
            f"analysts_renamed={r}, analysts_deleted={a}"
        )
        if dry_run:
            # Откат через raise — session.begin() сделает rollback, ничего не
            # запишется. Используем явный rollback вместо exception, чтобы
            # exit code остался 0.
            await session.rollback()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cleanup_test_data",
        description="Удаляет тестовые borrowers/analysts из БД перед demo.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет удалено, без записей в БД.",
    )
    group.add_argument(
        "--yes",
        action="store_true",
        help="Выполнить cleanup. Одна транзакция, на ошибке — rollback.",
    )
    args = parser.parse_args(argv)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _entry() -> int:
        try:
            return await _run(dry_run=args.dry_run)
        finally:
            await dispose_engine()

    return asyncio.run(_entry())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
