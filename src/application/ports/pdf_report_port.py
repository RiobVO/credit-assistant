"""PdfReportPort: контракт рендера PDF-досье.

Имплементация (``infrastructure.reports.pdf.WeasyPrintPdfRenderer``) живёт на
другой стороне DI-границы. Application-слой подаёт готовый ``DossierPdfBundle``
и получает байты PDF — никакого знания о Jinja2/WeasyPrint в use case нет.

Метод ``render`` синхронный: WeasyPrint и matplotlib — sync-библиотеки. Чтобы
не блокировать event loop FastAPI, use case оборачивает вызов в
``asyncio.to_thread`` (см. ``RenderDossierPdf.execute``).
"""

from __future__ import annotations

from typing import Protocol

from application.dto.dossier_pdf_bundle import DossierPdfBundle


class PdfReportPort(Protocol):
    def render(self, bundle: DossierPdfBundle) -> bytes: ...
