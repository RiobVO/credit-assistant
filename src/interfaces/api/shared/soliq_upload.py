"""POST /api/upload/soliq-xltx — превью VAT-периода из пары xltx-выгрузок.

Endpoint принимает multipart/form-data с двумя файлами (декларация НДС +
ilova-приложение №4 в любом порядке), ожидаемым ИНН заёмщика и месяцем
налогового периода. Парсеры классифицируют каждый файл через
``detect_format``; ровно один должен быть ``VAT_DECLARATION`` и ровно один
``VAT_REGISTRY_ILOVA``. Mapper ``to_soliq_chunk`` собирает один
``VatPeriodReport``. Endpoint возвращает структуру для предпросмотра в UI —
финальное досье строится отдельно через ``POST /api/manual-input``.

Best-effort: cell-level проблемы данных идут в ``parse_warnings``; ответ
всегда 200, кроме структурных ошибок (не та форма, отсутствие листов,
INN-mismatch, неверный размер пары).
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

from domain.value_objects.inn import INN, VALID_LENGTHS, InvalidInnError
from domain.value_objects.money import Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.format_detector import (
    SoliqXltxFormat,
)
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from infrastructure.adapters.soliq_xltx.snapshot_mapper import (
    XltxBorrowerMismatchError,
    to_soliq_chunk,
)
from infrastructure.adapters.soliq_xltx.vat_declaration_parser import VatDeclarationData
from infrastructure.adapters.soliq_xltx.vat_registry_parser import VatRegistryData

router = APIRouter(prefix="/api/upload", tags=["soliq-xltx"])

_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB — формы Soliq существенно меньше
_EXPECTED_FILE_COUNT = 2


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MoneyOutput(_StrictModel):
    amount: str  # Decimal сериализуем строкой — JSON float теряет точность
    currency: Literal["UZS", "USD"] = "UZS"


class DateRangeOutput(_StrictModel):
    start: str  # ISO 8601 (YYYY-MM-DD)
    end: str


class SoliqUploadResponse(_StrictModel):
    """Превью разобранного VAT-периода. UI пишет это в скрытое поле формы."""

    period: DateRangeOutput
    vat_declared: MoneyOutput | None
    esf_seller_vat_total: MoneyOutput | None
    organization_name: str | None  # best-effort: может быть None если не разобрался
    submitted_at: str | None  # ISO date или null
    diff_pct: str | None  # "1.19%" если оба значения есть, иначе null
    parse_warnings: list[str] = []  # best-effort cell-level замечания
    skipped_rows_count: int = 0  # сколько строк ilova пропущено


@router.post("/soliq-xltx", response_model=SoliqUploadResponse)
async def upload_soliq_xltx(
    files: Annotated[list[UploadFile], File(description="Два файла: декларация + ilova")],
    borrower_inn: Annotated[str, Form()],
    period_month: Annotated[int, Form(ge=1, le=12)],
) -> SoliqUploadResponse:
    """Парсит пару (декларация, ilova-реестр) → SoliqUploadResponse."""
    inn = _parse_inn(borrower_inn)
    declaration, registry = await _classify_pair(files)

    try:
        chunk, mapper_warnings = to_soliq_chunk(
            declaration=declaration,
            registry=registry,
            borrower_inn=inn,
            period_month=period_month,
        )
    except XltxBorrowerMismatchError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"INN в декларации ({exc.actual.masked}) не совпадает с "
                f"ожидаемым ({exc.expected.masked})"
            ),
        ) from exc

    period = chunk.vat_periods[0]
    diff_pct = _diff_pct(period.vat_declared, period.esf_seller_vat_total)

    return SoliqUploadResponse(
        period=DateRangeOutput(
            start=period.period.start.isoformat(),
            end=period.period.end.isoformat(),
        ),
        vat_declared=_money_out(period.vat_declared),
        esf_seller_vat_total=_money_out(period.esf_seller_vat_total),
        organization_name=declaration.header.organization_name,
        submitted_at=(
            period.submitted_at.isoformat() if period.submitted_at is not None else None
        ),
        diff_pct=diff_pct,
        parse_warnings=mapper_warnings,
        skipped_rows_count=registry.skipped_rows_count,
    )


def _parse_inn(raw: str) -> INN:
    cleaned = raw.strip()
    if len(cleaned) not in VALID_LENGTHS or not cleaned.isdigit():
        raise HTTPException(
            status_code=422,
            detail=f"INN должен содержать {sorted(VALID_LENGTHS)} цифр",
        )
    try:
        return INN(cleaned)
    except InvalidInnError as exc:
        raise HTTPException(
            status_code=422, detail=str(exc)
        ) from exc


async def _classify_pair(
    files: list[UploadFile],
) -> tuple[VatDeclarationData, VatRegistryData]:
    """Прочитать два файла, классифицировать и вернуть (декларация, реестр)."""
    if len(files) != _EXPECTED_FILE_COUNT:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Нужно загрузить ровно 2 файла (декларация + ilova-реестр); "
                f"получено: {len(files)}"
            ),
        )

    adapter = SoliqXltxAdapter()
    declaration: VatDeclarationData | None = None
    registry: VatRegistryData | None = None

    for upload in files:
        raw = await upload.read()
        if len(raw) > _MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Файл {upload.filename!r} больше {_MAX_FILE_BYTES} байт"
                ),
            )
        try:
            fmt = adapter.detect(raw)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Не удалось открыть файл {upload.filename!r}: {exc}",
            ) from exc

        try:
            if fmt is SoliqXltxFormat.VAT_DECLARATION:
                if declaration is not None:
                    raise HTTPException(
                        status_code=422,
                        detail="Получены две VAT-декларации — нужна одна декларация и одна ilova",
                    )
                parsed = adapter.parse(raw)
                assert isinstance(parsed, VatDeclarationData)
                declaration = parsed
            elif fmt is SoliqXltxFormat.VAT_REGISTRY_ILOVA:
                if registry is not None:
                    raise HTTPException(
                        status_code=422,
                        detail="Получены два ilova-реестра — нужна одна декларация и одна ilova",
                    )
                parsed = adapter.parse(raw)
                assert isinstance(parsed, VatRegistryData)
                registry = parsed
            else:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Файл {upload.filename!r} распознан как {fmt}; "
                        "ожидается VAT_DECLARATION или VAT_REGISTRY_ILOVA"
                    ),
                )
        except UnsupportedFormatError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Файл {upload.filename!r}: {exc}",
            ) from exc

    if declaration is None or registry is None:
        missing = "декларация" if declaration is None else "ilova-реестр"
        raise HTTPException(
            status_code=422,
            detail=f"В загруженной паре отсутствует: {missing}",
        )

    return declaration, registry


def _money_out(money: Money | None) -> MoneyOutput | None:
    if money is None:
        return None
    return MoneyOutput(amount=str(money.amount), currency=money.currency.value)


def _diff_pct(declared: Money | None, seller: Money | None) -> str | None:
    """Округлённый процент расхождения, либо ``None``."""
    if declared is None or seller is None:
        return None
    if declared.amount <= 0:
        return None
    pct = abs(declared.amount - seller.amount) / declared.amount * 100
    return f"{pct:.2f}%"
