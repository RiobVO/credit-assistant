"""Integration: scripts/backup_postgres.sh поверх real Postgres.

testcontainers Postgres → создаём fake-row → дёргаем backup script →
проверяем что dump-file существует, non-empty, retention работает.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.integration]


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "backup_postgres.sh"
)


def _bash_available() -> bool:
    return shutil.which("bash") is not None and shutil.which("pg_dump") is not None


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    target = tmp_path / "backups"
    target.mkdir()
    return target


def _run_script(
    backup_dir: Path,
    pg_url_parts: dict[str, str],
    *,
    retention_days: int = 7,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env.update(
        {
            "PGHOST": pg_url_parts["host"],
            "PGPORT": pg_url_parts["port"],
            "PGUSER": pg_url_parts["user"],
            "PGPASSWORD": pg_url_parts["password"],
            "PGDATABASE": pg_url_parts["database"],
            "BACKUP_DIR": str(backup_dir),
            "BACKUP_RETENTION_DAYS": str(retention_days),
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env=env,
        capture_output=True,
        timeout=120,
        check=False,
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


@pytest.mark.skipif(not _bash_available(), reason="bash + pg_dump required")
def test_backup_creates_non_empty_dump_file(
    pg_engine: AsyncEngine, backup_dir: Path
) -> None:
    parts = _pg_parts(pg_engine)
    result = _run_script(backup_dir, parts)

    assert result.returncode == 0, (
        f"script failed: stderr={result.stderr.decode(errors='replace')}"
    )
    dumps = list(backup_dir.glob("*.dump"))
    assert len(dumps) == 1, f"expected 1 dump, got {dumps}"
    assert dumps[0].stat().st_size > 0


@pytest.mark.skipif(not _bash_available(), reason="bash + pg_dump required")
def test_backup_retention_removes_old_files(
    pg_engine: AsyncEngine, backup_dir: Path
) -> None:
    # Подкладываем «старый» fake-dump с mtime 10 дней назад.
    old = backup_dir / "20260101T000000Z.dump"
    old.write_bytes(b"stale")
    old_mtime = time.time() - 10 * 86400
    os.utime(old, (old_mtime, old_mtime))

    parts = _pg_parts(pg_engine)
    result = _run_script(backup_dir, parts, retention_days=7)

    assert result.returncode == 0
    assert not old.exists(), "файл старше retention должен быть удалён"
    fresh = list(backup_dir.glob("*.dump"))
    assert len(fresh) == 1


@pytest.mark.skipif(not _bash_available(), reason="bash + pg_dump required")
def test_backup_fails_loudly_on_bad_credentials(
    pg_engine: AsyncEngine, backup_dir: Path
) -> None:
    parts = _pg_parts(pg_engine)
    parts["password"] = "wrong-password-zzz"
    result = _run_script(backup_dir, parts)

    assert result.returncode != 0
    # Exit 10 — наш контракт для pg_dump fail.
    assert result.returncode == 10, (
        f"expected exit 10, got {result.returncode}; "
        f"stderr={result.stderr.decode(errors='replace')}"
    )
    assert not list(backup_dir.glob("*.dump"))
