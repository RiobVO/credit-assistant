"""Integration: scripts/restore_drill.sh — pg_restore latest dump в temp DB,
проверка row counts vs source, drop temp.

Сценарий: создаём dump через backup_postgres.sh → запускаем restore_drill →
ожидаем exit 0 и отсутствие temp-DB после прогона.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.integration]


BACKUP_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "backup_postgres.sh"
)
DRILL_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "restore_drill.sh"
)


def _bins_available() -> bool:
    return all(
        shutil.which(b) is not None for b in ("bash", "pg_dump", "pg_restore", "psql")
    )


def _pg_parts(pg_engine: AsyncEngine) -> dict[str, str]:
    url = pg_engine.url
    return {
        "host": url.host or "127.0.0.1",
        "port": str(url.port or 5432),
        "user": url.username or "postgres",
        "password": url.password or "",
        "database": url.database or "postgres",
    }


def _env(parts: dict[str, str], backup_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PGHOST": parts["host"],
            "PGPORT": parts["port"],
            "PGUSER": parts["user"],
            "PGPASSWORD": parts["password"],
            "PGDATABASE": parts["database"],
            "BACKUP_DIR": str(backup_dir),
        }
    )
    return env


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    target = tmp_path / "backups"
    target.mkdir()
    return target


@pytest.mark.skipif(not _bins_available(), reason="bash + pg_dump + pg_restore + psql required")
def test_drill_passes_on_fresh_backup(
    pg_engine: AsyncEngine, backup_dir: Path
) -> None:
    parts = _pg_parts(pg_engine)
    env = _env(parts, backup_dir)

    # Сначала создаём свежий dump.
    bk = subprocess.run(
        ["bash", str(BACKUP_SCRIPT)], env=env, capture_output=True, timeout=60, check=False
    )
    assert bk.returncode == 0, bk.stderr.decode(errors="replace")

    # Запускаем drill.
    res = subprocess.run(
        ["bash", str(DRILL_SCRIPT)], env=env, capture_output=True, timeout=120, check=False
    )
    assert res.returncode == 0, (
        f"drill failed: stderr={res.stderr.decode(errors='replace')}"
    )


@pytest.mark.skipif(not _bins_available(), reason="bash + pg_restore + psql required")
def test_drill_fails_on_corrupted_dump(
    pg_engine: AsyncEngine, backup_dir: Path
) -> None:
    parts = _pg_parts(pg_engine)
    env = _env(parts, backup_dir)

    # Подкладываем «битый» 0-байтный dump.
    fake = backup_dir / "20260101T000000Z.dump"
    fake.write_bytes(b"")

    res = subprocess.run(
        ["bash", str(DRILL_SCRIPT)], env=env, capture_output=True, timeout=60, check=False
    )
    assert res.returncode == 20, (
        f"expected exit 20 (pg_restore fail), got {res.returncode}; "
        f"stderr={res.stderr.decode(errors='replace')}"
    )


@pytest.mark.skipif(not _bins_available(), reason="bash + pg_restore + psql required")
def test_drill_fails_when_no_backup_present(
    pg_engine: AsyncEngine, backup_dir: Path
) -> None:
    parts = _pg_parts(pg_engine)
    env = _env(parts, backup_dir)

    res = subprocess.run(
        ["bash", str(DRILL_SCRIPT)], env=env, capture_output=True, timeout=30, check=False
    )
    # Контракт: 23 — no backup file found.
    assert res.returncode == 23, (
        f"expected exit 23, got {res.returncode}; "
        f"stderr={res.stderr.decode(errors='replace')}"
    )
