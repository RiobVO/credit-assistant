"""Тесты SoliqXltxAdapter facade."""

from io import BytesIO
from pathlib import Path

import pytest

from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.format_detector import SoliqXltxFormat
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from infrastructure.adapters.soliq_xltx.vat_declaration_parser import VatDeclarationData
from infrastructure.adapters.soliq_xltx.vat_registry_parser import VatRegistryData
from tests.fixtures.soliq_xltx._factories import (
    build_form2_income_statement_wb,
    build_vat_declaration_wb,
    build_vat_registry_wb,
)


@pytest.fixture
def adapter() -> SoliqXltxAdapter:
    return SoliqXltxAdapter()


def _to_bytes(wb: object) -> bytes:
    """Сериализовать openpyxl Workbook в xltx-байты для тестирования source-вариантов."""
    buf = BytesIO()
    wb.save(buf)  # type: ignore[attr-defined]
    return buf.getvalue()


def test_dispatch_to_vat_declaration_parser(adapter: SoliqXltxAdapter) -> None:
    data = adapter.parse(_to_bytes(build_vat_declaration_wb()))
    assert isinstance(data, VatDeclarationData)
    assert data.header.borrower_inn.value == "306399449"


def test_dispatch_to_vat_registry_parser(adapter: SoliqXltxAdapter) -> None:
    wb = build_vat_registry_wb(
        sales=[("A", "200000000", "1", "01.03.2026", 100.0, 12.0)],
    )
    data = adapter.parse(_to_bytes(wb))
    assert isinstance(data, VatRegistryData)
    assert len(data.sales) == 1


def test_accepts_path_source(adapter: SoliqXltxAdapter, tmp_path: Path) -> None:
    file_path = tmp_path / "decl.xltx"
    build_vat_declaration_wb().save(file_path)
    data = adapter.parse(file_path)
    assert isinstance(data, VatDeclarationData)


def test_accepts_string_path_source(adapter: SoliqXltxAdapter, tmp_path: Path) -> None:
    file_path = tmp_path / "decl.xltx"
    build_vat_declaration_wb().save(file_path)
    data = adapter.parse(str(file_path))
    assert isinstance(data, VatDeclarationData)


def test_accepts_binary_io_source(adapter: SoliqXltxAdapter) -> None:
    buf = BytesIO()
    build_vat_declaration_wb().save(buf)
    buf.seek(0)
    data = adapter.parse(buf)
    assert isinstance(data, VatDeclarationData)


def test_unsupported_format_raises(adapter: SoliqXltxAdapter) -> None:
    # Form 2 распознаётся, но parser ещё не реализован в Day 1
    with pytest.raises(UnsupportedFormatError, match="not implemented"):
        adapter.parse(_to_bytes(build_form2_income_statement_wb()))


def test_detect_returns_format_without_parsing(adapter: SoliqXltxAdapter) -> None:
    fmt = adapter.detect(_to_bytes(build_vat_declaration_wb()))
    assert fmt == SoliqXltxFormat.VAT_DECLARATION

    fmt = adapter.detect(_to_bytes(build_vat_registry_wb()))
    assert fmt == SoliqXltxFormat.VAT_REGISTRY_ILOVA

    fmt = adapter.detect(_to_bytes(build_form2_income_statement_wb()))
    assert fmt == SoliqXltxFormat.FORM_2_INCOME_STATEMENT
