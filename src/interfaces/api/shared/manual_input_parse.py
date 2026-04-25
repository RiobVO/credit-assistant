"""POST /api/manual-input/parse-files — multi-file автозаполнение Step 2.

Принимает пачку xltx/CSV (FORM_2 income statement, VAT_DECLARATION,
VAT_REGISTRY_ILOVA), классифицирует каждый и сливает в ``ParsedFinancialsResponse``.
Frontend гидрирует форму Step 2 и помечает заполненные поля как read-only с
chip «из <source>».

Best-effort (CA-014, CA-027): endpoint всегда 200. Файл-level ошибки (битый
xltx, неизвестный формат, парсер не реализован) → warning в ответе, остальные
файлы обрабатываются.

Mode-gating: на bank install router закрыт ``Depends(get_current_analyst)``
(см. ``app.py``). На accountant install — открыт.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

from application.use_cases.parse_manual_input_files import (
    NamedFile,
    ParseManualInputFilesUseCase,
)
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter

router = APIRouter(prefix="/api/manual-input", tags=["manual-input"])

# Каждый xltx Soliq ≈ 20-30 КБ. 5 МБ × 10 файлов даёт запас, не позволяя DoS.
_MAX_FILE_BYTES = 5 * 1024 * 1024
_MAX_FILES = 10


class ParsedFinancialsResponse(BaseModel):
    """Структура ответа авто-парсинга. Все Decimal сериализуем строкой
    (ADR-0007: JSON float теряет точность на больших UZS-числах).
    """

    model_config = ConfigDict(extra="forbid")

    # int-ключ → str-Decimal. Pydantic v2 сериализует int-ключи как строки в JSON.
    revenue_by_year: dict[int, str]
    net_profit_by_year: dict[int, str]
    vat_declared_by_year: dict[int, str]
    taxes_paid_by_year: dict[int, str]
    # CA-041: column E xltx, «На конец отчётного периода» — текущий срез.
    assets_total: str | None
    liabilities_total: str | None
    # column D xltx, «На начало отчётного периода». Frontend пока не использует,
    # сохраняем для CA-037 (ROE с average_equity = (BoY+EoY)/2).
    assets_total_period_start: str | None
    liabilities_total_period_start: str | None
    source_trail: dict[str, str]
    parse_warnings: list[str]


@router.post("/parse-files", response_model=ParsedFinancialsResponse)
async def parse_files(
    files: Annotated[
        list[UploadFile],
        File(description="xltx/CSV-выгрузки my3.soliq.uz: FORM_2, VAT_DECLARATION, ESF CSV"),
    ],
) -> ParsedFinancialsResponse:
    if len(files) == 0:
        raise HTTPException(status_code=422, detail="Не загружено ни одного файла")
    if len(files) > _MAX_FILES:
        raise HTTPException(
            status_code=422,
            detail=f"Превышен лимит файлов за один запрос ({_MAX_FILES})",
        )

    named: list[NamedFile] = []
    for upload in files:
        raw = await upload.read()
        if len(raw) > _MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Файл {upload.filename!r} больше {_MAX_FILE_BYTES} байт",
            )
        named.append(NamedFile(name=upload.filename or "unknown", content=raw))

    usecase = ParseManualInputFilesUseCase(adapter=SoliqXltxAdapter())
    parsed = usecase.execute(named)

    return ParsedFinancialsResponse(
        revenue_by_year={y: str(v) for y, v in parsed.revenue_by_year.items()},
        net_profit_by_year={y: str(v) for y, v in parsed.net_profit_by_year.items()},
        vat_declared_by_year={y: str(v) for y, v in parsed.vat_declared_by_year.items()},
        taxes_paid_by_year={y: str(v) for y, v in parsed.taxes_paid_by_year.items()},
        assets_total=str(parsed.assets_total) if parsed.assets_total is not None else None,
        liabilities_total=(
            str(parsed.liabilities_total) if parsed.liabilities_total is not None else None
        ),
        assets_total_period_start=(
            str(parsed.assets_total_period_start)
            if parsed.assets_total_period_start is not None
            else None
        ),
        liabilities_total_period_start=(
            str(parsed.liabilities_total_period_start)
            if parsed.liabilities_total_period_start is not None
            else None
        ),
        source_trail=parsed.source_trail,
        parse_warnings=parsed.parse_warnings,
    )
