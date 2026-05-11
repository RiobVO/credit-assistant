"""Smoke-тесты WeasyPrintPdfRenderer.

WeasyPrint требует Pango/HarfBuzz нативно. На Windows-хосте без GTK runtime
импорт падает — поэтому тесты помечены ``@pytest.mark.integration`` и
дополнительно skip'аются на ``win32`` (запускайте в credit-api контейнере).
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from application.dto.dossier_pdf_bundle import DossierPdfBundle, TaxSummary
from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from application.dto.kpi_bundle import KpiBundle, KpiUnit, KpiValue, MonthlyRevenuePoint
from application.use_cases.load_dossier_for_view import DossierViewBundle
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.value_objects.inn import INN

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="WeasyPrint требует GTK runtime — запускайте в Docker (credit-api)",
    ),
]


PDF_MAGIC = b"%PDF-"


def _make_bundle() -> DossierPdfBundle:
    borrower = Borrower(
        inn=INN("306399449"),
        name="ООО «Тестовая фирма»",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 3, 14),
        director_name="Каримов Ш.А.",
        director_appointed_at=date(2018, 3, 14),
        okved_main="46.39",
        registered_address="г. Ташкент",
    )
    snapshot = BorrowerSnapshot(borrower=borrower, as_of=date(2026, 4, 30))

    view = DossierViewRecord(
        dossier_id=UUID("0f8a1234-0000-0000-0000-000000000001"),
        dossier=DossierRecord(
            score=12,
            recommendation="approve",
            severity_breakdown={"low": 1},
            red_flags=(),
            rules_version="v1.uz-msb",
            rules_evaluated=17,
        ),
        snapshot=snapshot,
        created_at=datetime(2026, 5, 10, 14, 32, tzinfo=UTC),
    )

    view_bundle = DossierViewBundle(
        view=view,
        kpis=KpiBundle(
            revenue_ltm=KpiValue(
                value=Decimal("21460000000"),
                unit=KpiUnit.UZS,
                yoy_pct=Decimal("18.2"),
                sparkline=(),
            ),
            ebitda=None,
            roe=None,
            debt_to_ebitda=None,
        ),
        monthly_revenue_24m=tuple(
            MonthlyRevenuePoint(
                month_start=date(2025, m, 1),
                revenue=Decimal(1_000_000_000 + m * 100_000_000),
                trend=Decimal(1_500_000_000),
                is_peak=(m == 12),
            )
            for m in range(1, 13)
        ),
    )

    return DossierPdfBundle(
        view_bundle=view_bundle,
        top_buyers=(),
        top_suppliers=(),
        tax_summary=TaxSummary(
            delays=(),
            max_delay_days=0,
            penalties_total=None,
            account_freezes_count_12m=0,
            has_freezes_12m=False,
        ),
    )


def test_render_returns_pdf_bytes_with_magic_header() -> None:
    from infrastructure.reports.pdf.pdf_renderer import WeasyPrintPdfRenderer

    renderer = WeasyPrintPdfRenderer(
        generated_at_factory=lambda: datetime(2026, 5, 10, 14, 32),
    )
    bundle = _make_bundle()

    pdf = renderer.render(bundle)

    assert pdf.startswith(PDF_MAGIC)
    assert len(pdf) > 5000, f"PDF слишком маленький: {len(pdf)} bytes"


def test_render_handles_empty_red_flags_and_empty_chart() -> None:
    from infrastructure.reports.pdf.pdf_renderer import WeasyPrintPdfRenderer

    renderer = WeasyPrintPdfRenderer(
        generated_at_factory=lambda: datetime(2026, 5, 10, 14, 32),
    )
    bundle = _make_bundle()
    # Чарт пустой — render_revenue_24m должен дать placeholder PNG.
    bundle = DossierPdfBundle(
        view_bundle=DossierViewBundle(
            view=bundle.view_bundle.view,
            kpis=bundle.view_bundle.kpis,
            monthly_revenue_24m=(),
        ),
        top_buyers=bundle.top_buyers,
        top_suppliers=bundle.top_suppliers,
        tax_summary=bundle.tax_summary,
    )

    pdf = renderer.render(bundle)

    assert pdf.startswith(PDF_MAGIC)
