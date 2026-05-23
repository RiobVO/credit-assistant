"""RenderDossierPdf: оркестратор рендера PDF-досье.

1) Берёт ``DossierViewBundle`` через уже существующий ``LoadDossierForView``
   (тот же путь, что и для GET endpoint — единственная точка чтения).
2) Считает агрегаты разделов D и E через ``pdf_data_aggregator``.
3) Phase 10: собирает ``Observations`` (executive summary cover) через
   ``observations_builder`` поверх snapshot+kpis+red_flags+RuleRegistry.
4) Резолвит ``BrandConfig`` через injected loader (env BRAND_ID → JSON).
5) T0.4 / ADR-0015: резолвит ``PdfMessages`` через injected
   ``pdf_messages_loader(lang)`` и пробрасывает rule_names в выбранной локали
   (``rule.name`` для ru, ``rule.name_uz`` для uz).
6) Передаёт готовый ``DossierPdfBundle`` в ``PdfReportPort.render``.

WeasyPrint и matplotlib — sync, поэтому ``port.render`` крутим в ``to_thread``,
чтобы FastAPI event loop не залипал на десятках мс рендера.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from application.dto.brand_config import BrandConfig
from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.dto.pdf_messages import PdfMessages
from application.ports.pdf_report_port import PdfReportPort
from application.services.observations_builder import BenchmarkLookup, build_observations
from application.services.pdf_data_aggregator import (
    compute_tax_summary,
    compute_top_buyers,
    compute_top_suppliers,
)
from application.use_cases.load_dossier_for_view import LoadDossierForView
from domain.rules.rule import Rule, RuleRegistry

Lang = Literal["ru", "uz"]
DEFAULT_LANG: Lang = "ru"


@dataclass(frozen=True, slots=True)
class RenderedPdf:
    """Результат рендера: байты + ``case_id`` для построения filename'а."""

    pdf_bytes: bytes
    case_id: str


class RenderDossierPdf:
    def __init__(
        self,
        loader: LoadDossierForView,
        renderer: PdfReportPort,
        rule_registry: RuleRegistry,
        brand_loader: Callable[[], BrandConfig],
        pdf_messages_loader: Callable[[Lang], PdfMessages],
        benchmark_catalog: BenchmarkLookup | None = None,
    ) -> None:
        self._loader = loader
        self._renderer = renderer
        self._registry = rule_registry
        self._brand_loader = brand_loader
        self._messages_loader = pdf_messages_loader
        self._benchmark_catalog = benchmark_catalog

    async def execute(
        self, dossier_id: UUID, lang: Lang = DEFAULT_LANG
    ) -> RenderedPdf | None:
        view_bundle = await self._loader.execute(dossier_id)
        if view_bundle is None:
            return None

        snapshot = view_bundle.view.snapshot
        messages = self._messages_loader(lang)
        observations = build_observations(
            snapshot=snapshot,
            kpis=view_bundle.kpis,
            red_flags=view_bundle.view.dossier.red_flags,
            registry=self._registry,
            messages=messages,
            benchmark_catalog=self._benchmark_catalog,
        )
        bundle = DossierPdfBundle(
            view_bundle=view_bundle,
            top_buyers=compute_top_buyers(snapshot),
            top_suppliers=compute_top_suppliers(snapshot),
            tax_summary=compute_tax_summary(snapshot),
            brand=self._brand_loader(),
            observations=observations,
            rule_names={r.id: _rule_name_for_lang(r, lang) for r in self._registry.rules},
            lang=lang,
            messages=messages,
        )
        pdf_bytes = await asyncio.to_thread(self._renderer.render, bundle)
        return RenderedPdf(pdf_bytes=pdf_bytes, case_id=view_bundle.view.case_id)


def _rule_name_for_lang(rule: Rule, lang: Lang) -> str:
    """RU → ``rule.name``; UZ → ``rule.name_uz`` с fallback на ``rule.name``.

    ``name_uz`` валидируется на load_registry как required (min_length=1),
    fallback нужен только для inline test-fixtures, конструирующих Rule
    напрямую без UZ-перевода (см. CA-DS17 / T0.4 commit 2).
    """
    if lang == "uz" and rule.name_uz:
        return rule.name_uz
    return rule.name
