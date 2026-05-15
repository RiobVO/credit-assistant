"""Тест use case RenderDossierPdf с fake-репо и fake-renderer."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from application.dto.brand_config import BrandConfig
from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from application.use_cases.load_dossier_for_view import LoadDossierForView
from application.use_cases.render_dossier_pdf import RenderDossierPdf
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.rules.rule import RuleRegistry
from domain.value_objects.inn import INN


def _brand() -> BrandConfig:
    return BrandConfig(
        id="test",
        name="Test Bank",
        tagline="Test",
        logo_mark="TB",
        primary="#000",
        primary_hover="#111",
        primary_soft="#eee",
        primary_ink="#222",
        primary_ring="rgba(0,0,0,0.2)",
    )


def _empty_registry() -> RuleRegistry:
    return RuleRegistry(rules=[])


class _FakeRepo:
    def __init__(self, record: DossierViewRecord | None) -> None:
        self._record = record

    async def get_view_by_id(self, dossier_id: UUID) -> DossierViewRecord | None:
        return self._record


class _FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[DossierPdfBundle] = []

    def render(self, bundle: DossierPdfBundle) -> bytes:
        self.calls.append(bundle)
        return b"%PDF-fake"


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов И.И.",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="г. Ташкент",
    )


def _record_with_buyers() -> DossierViewRecord:
    cp = Counterparty(inn=INN("200000001"), name="Buyer A", registration_date=date(2020, 1, 1))
    snap = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 1),
        counterparties_buyers=[cp],
        buyer_revenue_share={"200000001": Decimal("0.30")},
    )
    return DossierViewRecord(
        dossier_id=uuid4(),
        dossier=DossierRecord(
            score=10,
            recommendation="approve",
            severity_breakdown={},
            red_flags=(),
            rules_version="v1",
            rules_evaluated=17,
        ),
        snapshot=snap,
        created_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_none_when_dossier_missing() -> None:
    loader = LoadDossierForView(_FakeRepo(None))
    renderer = _FakeRenderer()
    use_case = RenderDossierPdf(
        loader, renderer, rule_registry=_empty_registry(), brand_loader=_brand,
    )

    result = await use_case.execute(uuid4())

    assert result is None
    assert renderer.calls == []


@pytest.mark.asyncio
async def test_passes_enriched_bundle_to_renderer() -> None:
    record = _record_with_buyers()
    loader = LoadDossierForView(_FakeRepo(record))
    renderer = _FakeRenderer()
    use_case = RenderDossierPdf(
        loader, renderer, rule_registry=_empty_registry(), brand_loader=_brand,
    )

    result = await use_case.execute(record.dossier_id)

    assert result == b"%PDF-fake"
    assert len(renderer.calls) == 1
    bundle = renderer.calls[0]
    assert bundle.view_bundle.view is record
    # Топ-N считается из counterparties + share map
    assert len(bundle.top_buyers) == 1
    assert bundle.top_buyers[0].inn == "200000001"
    assert bundle.top_buyers[0].share_pct == Decimal("30.00")
    # Tax summary пустой — событий не было
    assert bundle.tax_summary.max_delay_days == 0
    assert bundle.tax_summary.has_freezes_12m is False
    # Phase 10: brand резолвится через injected loader
    assert bundle.brand.id == "test"
    # Phase 10: observations собираются всегда (empty risks при flags=())
    assert bundle.observations.risks == ()
    # Phase 10: rule_names mapping из registry (пустой → {})
    assert bundle.rule_names == {}
