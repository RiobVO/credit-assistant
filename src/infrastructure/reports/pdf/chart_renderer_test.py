"""Тесты chart_renderer: PNG magic bytes + размер + отказ-сценарии."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from application.dto.kpi_bundle import MonthlyRevenuePoint
from infrastructure.reports.pdf.chart_renderer import (
    render_revenue_24m,
    render_sparkline,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _point(
    month: int, revenue: int, *, year: int = 2025, peak: bool = False
) -> MonthlyRevenuePoint:
    return MonthlyRevenuePoint(
        month_start=date(year, month, 1),
        revenue=Decimal(revenue),
        trend=Decimal(revenue),
        is_peak=peak,
    )


def test_revenue_24m_returns_png_for_full_series() -> None:
    points = [_point(m, 1_000_000_000 + m * 100_000_000) for m in range(1, 13)]
    points[5] = _point(6, 5_000_000_000, peak=True)

    png = render_revenue_24m(points)

    assert png.startswith(PNG_MAGIC), "должны быть PNG magic bytes"
    assert len(png) > 1500, f"PNG слишком маленький: {len(png)} bytes"


def test_revenue_24m_empty_input_returns_placeholder_png() -> None:
    png = render_revenue_24m([])

    assert png.startswith(PNG_MAGIC)
    # Плейсхолдер с текстом — всё равно валидный PNG, размер ненулевой
    assert len(png) > 500


def test_sparkline_returns_png_for_normal_series() -> None:
    png = render_sparkline([Decimal(i) for i in range(10)], tone="up")

    assert png.startswith(PNG_MAGIC)
    assert len(png) > 200


def test_sparkline_too_short_returns_blank_png() -> None:
    """Менее 2 точек — рисуем пустой PNG, шаблон не отображает блок."""
    png = render_sparkline([Decimal(1)], tone="up")

    assert png.startswith(PNG_MAGIC)


def test_sparkline_tone_down_uses_red_color() -> None:
    """Smoke: tone=down не падает и возвращает PNG (визуально красный)."""
    png = render_sparkline([Decimal(10), Decimal(8), Decimal(5)], tone="down")
    assert png.startswith(PNG_MAGIC)
