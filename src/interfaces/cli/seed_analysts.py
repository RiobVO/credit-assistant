"""CLI: создать/обновить банковского аналитика.

Запуск:
    uv run python -m interfaces.cli.seed_analysts \
        --email ivanov@bank.uz --password 'changeme' --full-name 'Иванов И.И.'

При совпадении email — обновляет password_hash, full_name, role, is_active.
Используется для dev/POC; в production seed выполняется через защищённый
канал банковского администратора.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import dispose_engine, get_session_factory
from infrastructure.persistence.models.analyst import AnalystORM


async def _upsert_analyst(
    email: str,
    password: str,
    full_name: str,
    role: str,
    is_active: bool,
) -> tuple[str, str]:
    """Upsert по email. Возвращает (action, analyst_id) где action ∈ {created, updated}."""
    hasher = PasswordHasher(rounds=12)
    password_hash = hasher.hash(password)
    factory = get_session_factory()
    async with factory() as session, session.begin():
        existing = (
            await session.execute(select(AnalystORM).where(AnalystORM.email == email))
        ).scalar_one_or_none()
        if existing is None:
            new = AnalystORM(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                is_active=is_active,
            )
            session.add(new)
            await session.flush()
            return "created", str(new.id)
        existing.password_hash = password_hash
        existing.full_name = full_name
        existing.role = role
        existing.is_active = is_active
        await session.flush()
        return "updated", str(existing.id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="seed_analysts",
        description="Создаёт или обновляет банковского аналитика для Bank Mode.",
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", default="analyst")
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Создать/обновить как неактивного — login будет отклонён.",
    )
    args = parser.parse_args(argv)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        action, analyst_id = asyncio.run(
            _upsert_analyst(
                email=args.email,
                password=args.password,
                full_name=args.full_name,
                role=args.role,
                is_active=not args.inactive,
            )
        )
        print(f"{action}: {args.email} -> {analyst_id}")
        return 0
    finally:
        asyncio.run(dispose_engine())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
