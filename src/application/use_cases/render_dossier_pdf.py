"""RenderDossierPdf: оркестратор рендера PDF-досье.

1) Берёт ``DossierViewBundle`` через уже существующий ``LoadDossierForView``
   (тот же путь, что и для GET endpoint — единственная точка чтения).
2) Считает агрегаты разделов D и E через ``pdf_data_aggregator``.
3) Phase 10: собирает ``Observations`` (executive summary cover) через
   ``observations_builder`` поверх snapshot+kpis+red_flags+RuleRegistry.
4) Резолвит ``BrandConfig`` через injected loader (env BRAND_ID → JSON).
5) Передаёт готовый ``DossierPdfBundle`` в ``PdfReportPort.render``.

WeasyPrint и matplotlib — sync, поэтому ``port.render`` крутим в ``to_thread``,
чтобы FastAPI event loop не залипал на десятках мс рендера.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import UUID

from application.dto.brand_config import BrandConfig
from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.ports.pdf_report_port import PdfReportPort
from application.services.observations_builder import build_observations
from application.services.pdf_data_aggregator import (
    compute_tax_summary,
    compute_top_buyers,
    compute_top_suppliers,
)
from application.use_cases.load_dossier_for_view import LoadDossierForView
from domain.rules.rule import RuleRegistry


class RenderDossierPdf:
    def __init__(
        self,
        loader: LoadDossierForView,
        renderer: PdfReportPort,
        rule_registry: RuleRegistry,
        brand_loader: Callable[[], BrandConfig],
    ) -> None:
        self._loader = loader
        self._renderer = renderer
        self._registry = rule_registry
        self._brand_loader = brand_loader

    async def execute(self, dossier_id: UUID) -> bytes | None:
        view_bundle = await self._loader.execute(dossier_id)
        if view_bundle is None:
            return None

        snapshot = view_bundle.view.snapshot
        observations = build_observations(
            snapshot=snapshot,
            kpis=view_bundle.kpis,
            red_flags=view_bundle.view.dossier.red_flags,
            registry=self._registry,
        )
        bundle = DossierPdfBundle(
            view_bundle=view_bundle,
            top_buyers=compute_top_buyers(snapshot),
            top_suppliers=compute_top_suppliers(snapshot),
            tax_summary=compute_tax_summary(snapshot),
            brand=self._brand_loader(),
            observations=observations,
            rule_names={r.id: r.name for r in self._registry.rules},
        )
        return await asyncio.to_thread(self._renderer.render, bundle)
