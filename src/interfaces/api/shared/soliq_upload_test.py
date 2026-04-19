"""Integration-тесты POST /api/upload/soliq-xltx.

Используют synthetic factories из tests/fixtures/soliq_xltx/_factories.py для
конструирования xltx-байтов в памяти. TestClient FastAPI'я.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl.workbook.workbook import Workbook

from interfaces.api.app import create_app
from tests.fixtures.soliq_xltx._factories import (
    build_form2_income_statement_wb,
    build_vat_declaration_wb,
    build_vat_registry_wb,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _wb_bytes(wb: Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _decl_bytes(**kwargs: object) -> bytes:
    return _wb_bytes(build_vat_declaration_wb(**kwargs))  # type: ignore[arg-type]


def _ilova_bytes(
    sales: list[tuple[str, str | None, str, str, float, float]] | None = None,
) -> bytes:
    return _wb_bytes(build_vat_registry_wb(sales=tuple(sales or [])))


class TestSuccess:
    def test_returns_period_and_amounts_for_valid_pair(self, client: TestClient) -> None:
        decl = _decl_bytes()
        ilova = _ilova_bytes(
            sales=[
                ("ООО Покупатель", "200000020", "INV-1", "15.03.2026", 100_000_000.0, 12_000_000.0),
                ("ИП", None, "INV-2", "20.03.2026", 50_000_000.0, 6_000_000.0),
            ]
        )
        ct = "application/vnd.ms-excel.template.macroEnabled.12"
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("decl.xltx", decl, ct)),
                ("files", ("ilova.xltx", ilova, ct)),
            ],
            data={"borrower_inn": "306399449", "period_month": "3"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["period"] == {"start": "2026-03-01", "end": "2026-03-31"}
        assert body["vat_declared"]["amount"] == "62799985.69"
        # Decimal("100000000.0") + Decimal("12000000.0") + ... — точная сумма НДС.
        assert body["esf_seller_vat_total"]["amount"] == "18000000"
        assert body["organization_name"].startswith('"AZ RUHDIL SAVDO"')
        assert body["submitted_at"] == "2026-04-20"
        # diff_pct формата "NN.NN%" — в этой паре сильное расхождение, главное что заполнено.
        assert body["diff_pct"] is not None
        assert body["diff_pct"].endswith("%")

    def test_accepts_files_in_reverse_order(self, client: TestClient) -> None:
        # Проверка auto-detect: ilova первым, декларация вторым.
        decl = _decl_bytes()
        ilova = _ilova_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("ilova.xltx", ilova, "application/octet-stream")),
                ("files", ("decl.xltx", decl, "application/octet-stream")),
            ],
            data={"borrower_inn": "306399449", "period_month": "3"},
        )
        assert resp.status_code == 200, resp.text


class TestValidationErrors:
    def test_two_declarations_rejected(self, client: TestClient) -> None:
        decl = _decl_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("a.xltx", decl, "application/octet-stream")),
                ("files", ("b.xltx", decl, "application/octet-stream")),
            ],
            data={"borrower_inn": "306399449", "period_month": "3"},
        )
        assert resp.status_code == 422
        assert "две VAT-декларации" in resp.json()["detail"]

    def test_two_ilovas_rejected(self, client: TestClient) -> None:
        ilova = _ilova_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("a.xltx", ilova, "application/octet-stream")),
                ("files", ("b.xltx", ilova, "application/octet-stream")),
            ],
            data={"borrower_inn": "306399449", "period_month": "3"},
        )
        assert resp.status_code == 422
        assert "два ilova" in resp.json()["detail"]

    def test_one_file_rejected(self, client: TestClient) -> None:
        decl = _decl_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[("files", ("decl.xltx", decl, "application/octet-stream"))],
            data={"borrower_inn": "306399449", "period_month": "3"},
        )
        assert resp.status_code == 422
        assert "ровно 2 файла" in resp.json()["detail"]

    def test_wrong_format_rejected(self, client: TestClient) -> None:
        # Form №2 не подходит — отдельный формат, не VAT-декларация и не ilova.
        form2 = _wb_bytes(build_form2_income_statement_wb())
        ilova = _ilova_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("form2.xltx", form2, "application/octet-stream")),
                ("files", ("ilova.xltx", ilova, "application/octet-stream")),
            ],
            data={"borrower_inn": "306399449", "period_month": "3"},
        )
        assert resp.status_code == 422
        assert "form_2_income_statement" in resp.json()["detail"]

    def test_inn_mismatch_rejected(self, client: TestClient) -> None:
        decl = _decl_bytes()  # ИНН 306399449 в декларации
        ilova = _ilova_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("decl.xltx", decl, "application/octet-stream")),
                ("files", ("ilova.xltx", ilova, "application/octet-stream")),
            ],
            data={"borrower_inn": "123456789", "period_month": "3"},  # другой ИНН
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "не совпадает" in body["detail"]

    def test_invalid_period_month_rejected(self, client: TestClient) -> None:
        decl = _decl_bytes()
        ilova = _ilova_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("decl.xltx", decl, "application/octet-stream")),
                ("files", ("ilova.xltx", ilova, "application/octet-stream")),
            ],
            data={"borrower_inn": "306399449", "period_month": "13"},
        )
        # FastAPI валидирует ge=1, le=12 на уровне Form — отдаёт 422 от Pydantic.
        assert resp.status_code == 422

    def test_invalid_inn_rejected(self, client: TestClient) -> None:
        decl = _decl_bytes()
        ilova = _ilova_bytes()
        resp = client.post(
            "/api/upload/soliq-xltx",
            files=[
                ("files", ("decl.xltx", decl, "application/octet-stream")),
                ("files", ("ilova.xltx", ilova, "application/octet-stream")),
            ],
            data={"borrower_inn": "abc", "period_month": "3"},
        )
        assert resp.status_code == 422
