"""Integration test: прогон реальных xltx через format_detector → parser.

Сканирует:
- ``tests/fixtures/soliq_xltx/*_full.xltx`` — реальные выгрузки (gitignored, локальные).
- ``tests/fixtures/soliq_xltx/*_anon.xltx`` — анонимизированные (в git, CI прогоняет).

Если ни одного файла нет — ``pytest.skip`` (CI без локальных fixtures всё равно
пройдёт зелёным, не false-fail).

Контракт T0.1: каждый поддержанный xltx-формат парсится без unexpected
``parse_warnings``. Все 5 форматов покрыты (T2.3 закрыл PROFIT_TAX).
UNKNOWN — fail (детектор обязан опознать любой реальный файл — иначе либо
формат изменился, либо нужен новый sentinel).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from infrastructure.adapters.soliq_xltx.format_detector import (
    SoliqXltxFormat,
    detect_format,
)
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "soliq_xltx"


def _real_xltx_files() -> list[Path]:
    if not _FIXTURES_DIR.is_dir():
        return []
    full = sorted(_FIXTURES_DIR.glob("*_full.xltx"))
    anon = sorted(_FIXTURES_DIR.glob("*_anon.xltx"))
    return [*full, *anon]


_FILES = _real_xltx_files()


@pytest.mark.skipif(
    not _FILES,
    reason=(
        "no real xltx fixtures (*_full.xltx, *_anon.xltx) — "
        "см. tests/fixtures/soliq_xltx/README.md"
    ),
)
@pytest.mark.parametrize("xltx_path", _FILES, ids=lambda p: p.name)
def test_real_xltx_parses_without_unexpected_warnings(xltx_path: Path) -> None:
    wb = load_workbook(filename=str(xltx_path), data_only=True, read_only=False)
    try:
        fmt = detect_format(wb)
    finally:
        wb.close()

    assert fmt is not SoliqXltxFormat.UNKNOWN, (
        f"detect_format не опознал {xltx_path.name} — "
        "либо файл повреждён, либо нужен новый sentinel в format_detector"
    )

    dto = SoliqXltxAdapter().parse(xltx_path)
    warnings = list(getattr(dto, "parse_warnings", []))

    assert warnings == [], (
        f"unexpected parse_warnings в {xltx_path.name} (fmt={fmt.value}):\n"
        + "\n".join(f"  - {w}" for w in warnings)
    )
