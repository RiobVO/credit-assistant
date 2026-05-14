"""SqlAlchemyDossierRepository: insert-only результат прогона правил."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.bank_dossier_summary import (
    BankDailyStats,
    BankDossierListItem,
    BankDossierListPage,
    BorrowerSearchHit,
)
from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from infrastructure.persistence.mappers.borrower_mapper import borrower_from_orm
from infrastructure.persistence.mappers.dossier_mapper import (
    dossier_record_from_orm_columns,
    red_flags_to_jsonb,
)
from infrastructure.persistence.mappers.snapshot_mapper import snapshot_from_payload
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM


class SqlAlchemyDossierRepository:
    """Реализация ``DossierRepositoryPort``. Досье иммутабельно — только save/get."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        record: DossierRecord,
        snapshot_id: UUID,
        case_id: str,
        *,
        source_mode: str = "accountant",
        created_by_analyst_id: UUID | None = None,
    ) -> UUID:
        new_id = uuid4()
        orm = DossierORM(
            id=new_id,
            snapshot_id=snapshot_id,
            score=record.score,
            recommendation=record.recommendation,
            severity_breakdown=dict(record.severity_breakdown),
            red_flags=red_flags_to_jsonb(record.red_flags),
            rules_version=record.rules_version,
            rules_evaluated=record.rules_evaluated,
            source_mode=source_mode,
            created_by_analyst_id=created_by_analyst_id,
            case_id=case_id,
        )
        self._session.add(orm)
        await self._session.flush()
        return new_id

    async def get_by_id(self, dossier_id: UUID) -> DossierRecord | None:
        orm = await self._session.get(DossierORM, dossier_id)
        if orm is None:
            return None
        return dossier_record_from_orm_columns(
            score=orm.score,
            recommendation=orm.recommendation,
            severity_breakdown=orm.severity_breakdown,
            red_flags=orm.red_flags,
            rules_version=orm.rules_version,
            rules_evaluated=orm.rules_evaluated,
        )

    async def get_view_by_id(self, dossier_id: UUID) -> DossierViewRecord | None:
        """Один SELECT с двумя JOIN: dossier + snapshot + borrower.

        Используется экраном /dossier/[id] (Phase 3.B). Альтернатива — три
        отдельных запроса через ``snapshot_repo.get_by_id`` и
        ``dossier_repo.get_by_id``; одиночный JOIN дешевле и атомарнее по
        чтению (snapshot не пропадёт между запросами благодаря FK RESTRICT,
        но один round-trip читается как одна операция).
        """
        stmt = (
            select(DossierORM, BorrowerSnapshotORM, BorrowerORM)
            .join(
                BorrowerSnapshotORM, DossierORM.snapshot_id == BorrowerSnapshotORM.id
            )
            .join(BorrowerORM, BorrowerSnapshotORM.borrower_id == BorrowerORM.id)
            .where(DossierORM.id == dossier_id)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        dossier_orm, snapshot_orm, borrower_orm = row

        borrower = borrower_from_orm(borrower_orm)
        snapshot = snapshot_from_payload(snapshot_orm.payload, borrower)
        dossier_record = dossier_record_from_orm_columns(
            score=dossier_orm.score,
            recommendation=dossier_orm.recommendation,
            severity_breakdown=dossier_orm.severity_breakdown,
            red_flags=dossier_orm.red_flags,
            rules_version=dossier_orm.rules_version,
            rules_evaluated=dossier_orm.rules_evaluated,
        )
        return DossierViewRecord(
            dossier_id=dossier_orm.id,
            dossier=dossier_record,
            snapshot=snapshot,
            created_at=dossier_orm.created_at,
            case_id=dossier_orm.case_id,
        )

    async def find_search_hit_by_inn(self, inn: str) -> BorrowerSearchHit:
        """Bank search: lookup borrower по INN + последнее bank-mode досье.

        Возвращает три варианта:
        * borrower не найден → ``found=False``, всё None
        * borrower найден, bank-mode досье нет → ``found=True``, ``dossier_id=None``
        * borrower найден, есть bank-mode досье → полный hit
        """
        borrower_orm = (
            await self._session.execute(
                select(BorrowerORM).where(BorrowerORM.inn == inn)
            )
        ).scalar_one_or_none()
        if borrower_orm is None:
            return BorrowerSearchHit(
                found=False,
                borrower_id=None,
                borrower_name=None,
                dossier_id=None,
                score=None,
                created_at=None,
            )

        # Последнее bank-mode досье. JOIN на snapshots (FK borrower_id), фильтр
        # по source_mode='bank'. Если папа загружал в accountant-mode — здесь не показываем.
        latest = (
            await self._session.execute(
                select(DossierORM)
                .join(
                    BorrowerSnapshotORM,
                    DossierORM.snapshot_id == BorrowerSnapshotORM.id,
                )
                .where(
                    BorrowerSnapshotORM.borrower_id == borrower_orm.id,
                    DossierORM.source_mode == "bank",
                )
                .order_by(desc(DossierORM.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest is None:
            return BorrowerSearchHit(
                found=True,
                borrower_id=borrower_orm.id,
                borrower_name=borrower_orm.name,
                dossier_id=None,
                score=None,
                created_at=None,
            )
        return BorrowerSearchHit(
            found=True,
            borrower_id=borrower_orm.id,
            borrower_name=borrower_orm.name,
            dossier_id=latest.id,
            score=latest.score,
            created_at=latest.created_at,
        )

    async def list_bank_dossiers(
        self,
        *,
        analyst_id: UUID,
        only_mine: bool,
        query: str | None,
        page: int,
        page_size: int,
    ) -> BankDossierListPage:
        """Пагинированная история bank-mode досье с опциональным фильтром.

        ``only_mine``: ограничивает ``created_by_analyst_id = analyst_id``.
        ``query``: ILIKE по borrower.inn ИЛИ borrower.name. None/пусто — без фильтра.
        """
        base_filters = [DossierORM.source_mode == "bank"]
        if only_mine:
            base_filters.append(DossierORM.created_by_analyst_id == analyst_id)
        if query:
            pattern = f"%{query.strip()}%"
            base_filters.append(
                or_(BorrowerORM.inn.ilike(pattern), BorrowerORM.name.ilike(pattern))
            )

        count_stmt = (
            select(func.count(DossierORM.id))
            .join(
                BorrowerSnapshotORM, DossierORM.snapshot_id == BorrowerSnapshotORM.id
            )
            .join(BorrowerORM, BorrowerSnapshotORM.borrower_id == BorrowerORM.id)
            .where(*base_filters)
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        items_stmt = (
            select(DossierORM, BorrowerORM, AnalystORM)
            .join(
                BorrowerSnapshotORM, DossierORM.snapshot_id == BorrowerSnapshotORM.id
            )
            .join(BorrowerORM, BorrowerSnapshotORM.borrower_id == BorrowerORM.id)
            .outerjoin(AnalystORM, DossierORM.created_by_analyst_id == AnalystORM.id)
            .where(*base_filters)
            .order_by(desc(DossierORM.created_at))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self._session.execute(items_stmt)).all()
        items = tuple(
            BankDossierListItem(
                dossier_id=d.id,
                inn=b.inn,
                borrower_name=b.name,
                score=d.score,
                recommendation=d.recommendation,
                created_at=d.created_at,
                analyst_id=a.id if a is not None else None,
                analyst_full_name=a.full_name if a is not None else None,
            )
            for d, b, a in rows
        )
        return BankDossierListPage(
            items=items,
            total=int(total),
            page=page,
            page_size=page_size,
        )

    async def get_bank_daily_stats(self, today: date) -> BankDailyStats:
        """Bank-mode daily stats для live-strip на /search.

        Аггрегирует bank-mode dossiers, созданные в ``today`` (UTC date),
        в три числа: collected_today, approved_pct (целое 0..100 или None если
        today=0), in_review_today. Один SELECT по `created_at` >= today UTC
        midnight AND < next UTC midnight.

        ``today`` обычно ``date.today()`` (UTC в проде; для тестов inject).
        """
        start = datetime.combine(today, time.min, tzinfo=UTC)
        end = datetime.combine(today, time.max, tzinfo=UTC)

        stmt = select(
            func.count(DossierORM.id).label("collected"),
            func.count(DossierORM.id)
            .filter(DossierORM.recommendation == "approve")
            .label("approved"),
            func.count(DossierORM.id)
            .filter(DossierORM.recommendation == "review")
            .label("in_review"),
        ).where(
            DossierORM.source_mode == "bank",
            DossierORM.created_at >= start,
            DossierORM.created_at <= end,
        )
        row = (await self._session.execute(stmt)).one()
        collected = int(row.collected)
        approved = int(row.approved)
        in_review = int(row.in_review)
        approved_pct = (
            round(approved * 100 / collected) if collected > 0 else None
        )
        return BankDailyStats(
            collected_today=collected,
            approved_pct=approved_pct,
            in_review_today=in_review,
        )
