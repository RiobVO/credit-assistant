"""RenderDossierPdf: оркестратор рендера PDF-досье.

1) Берёт ``DossierViewBundle`` через уже существующий ``LoadDossierForView``
   (тот же путь, что и для GET endpoint — единственная точка чтения).
2) Считает агрегаты разделов D и E через ``pdf_data_aggregator``.
3) Передаёт готовый ``DossierPdfBundle`` в ``PdfReportPort.render``.

WeasyPrint и matplotlib — sync, поэтому ``port.render`` крутим в ``to_thread``,
чтобы FastAPI event loop не залипал на десятках мс рендера.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.ports.pdf_report_port import PdfReportPort
from application.services.pdf_data_aggregator import (
    compute_tax_summary,
    compute_top_buyers,
    compute_top_suppliers,
)
from application.use_cases.load_dossier_for_view import LoadDossierForView


class RenderDossierPdf:
    def __init__(self, loader: LoadDossierForView, renderer: PdfReportPort) -> None:
        self._loader = loader
        self._renderer = renderer

    async def execute(self, dossier_id: UUID) -> bytes | None:
        view_bundle = await self._loader.execute(dossier_id)
        if view_bundle is None:
            return None

        snapshot = view_bundle.view.snapshot
        bundle = DossierPdfBundle(
            view_bundle=view_bundle,
            top_buyers=compute_top_buyers(snapshot),
            top_suppliers=compute_top_suppliers(snapshot),
            tax_summary=compute_tax_summary(snapshot),
        )
        return await asyncio.to_thread(self._renderer.render, bundle)
