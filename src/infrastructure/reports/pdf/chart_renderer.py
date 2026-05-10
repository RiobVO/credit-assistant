"""Matplotlib-чарты для PDF-досье. Возвращают PNG bytes для встройки в шаблон.

Два чарта на отчёт:

* ``render_revenue_24m`` — раздел C: помесячная выручка с акцентом на топ-3
  пиков и линией 12-мес rolling-тренда (повторяет логику экрана досье).
* ``render_sparkline`` — мини-чарт для KPI Revenue LTM на странице G/обложке.

Backend ``matplotlib.use("Agg")`` ставится при импорте модуля — без GUI и
без Tk. PNG сериализуется в ``BytesIO`` и встраивается в шаблон через
data-URI base64 (``WeasyPrintPdfRenderer`` делает encode).

Сетка цветов синхронизирована с frontend ``globals.css``: основной — Indigo
``#1E55C9``, акцент пиков — Warning Amber ``#B8730E``, тренд — Primary Blue
700 ``#1947AA``. Шрифт оси — DejaVu Sans (системный fallback в python:slim);
для финального отчёта Inter подаётся на уровне HTML, не PNG-чарта.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from decimal import Decimal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from application.dto.kpi_bundle import MonthlyRevenuePoint

# --- константы стилей ----------------------------------------------------

COLOR_BAR = "#9DA8BC"  # neutral gray для обычных столбцов
COLOR_PEAK = "#B8730E"  # warning amber для top-3 пиков
COLOR_TREND = "#1947AA"  # primary blue 700 для линии тренда
COLOR_AXIS = "#5A6478"  # ink-500 для тиков и подписей
COLOR_GRID = "#E4E7EC"  # ca-border для горизонтальной сетки

DPI_DEFAULT = 144
SPARKLINE_DPI = 144

_RU_MONTHS = (
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)


def _format_month_short(month_index: int, year: int) -> str:
    """``2025-12`` → ``"дек 25"``. Используется для оси X."""
    return f"{_RU_MONTHS[month_index - 1]} {year % 100:02d}"


def render_revenue_24m(
    points: Sequence[MonthlyRevenuePoint],
    *,
    width_in: float = 8.5,
    height_in: float = 2.6,
    dpi: int = DPI_DEFAULT,
    has_annual_revenue: bool = False,
) -> bytes:
    """PNG-чарт «выручка по месяцам» для раздела C.

    Пустой ``points`` — placeholder-PNG с текстом empty state. Layout
    сохраняется: шаблон вставляет PNG, не зная «есть данные или нет».

    CA-046: ``has_annual_revenue`` синхронизирует копирайт с UI досье (CA-036).
    Аналитик не должен видеть «нет данных», когда годовые показатели в
    разделе B уже сформированы — это два разных уровня детализации.

    * ``True``  → «Помесячная динамика недоступна» (годовые из FORM_2 есть,
      нужен ESF CSV из my3.soliq.uz для помесячной разбивки).
    * ``False`` → «Нет данных о выручке» (INSUFFICIENT: ни годовых, ни
      помесячных — флоу загрузки на Шаге 2).
    """
    fig: Figure
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)

    if not points:
        if has_annual_revenue:
            title = "Помесячная динамика недоступна"
            hint = (
                "Годовая выручка вычислена из Формы №2. Загрузите ESF CSV\n"
                "из my3.soliq.uz для помесячной разбивки."
            )
        else:
            title = "Нет данных о выручке"
            hint = (
                "Загрузите выгрузку Soliq на Шаге 2 формы или укажите\n"
                "помесячный оборот вручную."
            )
        # Light-grey placeholder rect — даёт PNG полную ширину и визуальную
        # границу чарта (как .chart-placeholder в design-reference). Без него
        # ``bbox_inches="tight"`` обрезал PNG до bounding-box центрированного
        # текста, и шаблон отрисовывал узкий лоскут 200×80px.
        ax.add_patch(
            Rectangle(
                (0, 0), 1, 1,
                transform=ax.transAxes,
                facecolor="#FAFBFC",
                edgecolor=COLOR_GRID,
                linewidth=0.8,
                zorder=0,
            ),
        )
        ax.text(
            0.5, 0.62, title,
            ha="center", va="center",
            transform=ax.transAxes,
            color=COLOR_AXIS, fontsize=11, fontweight="semibold",
            zorder=1,
        )
        ax.text(
            0.5, 0.36, hint,
            ha="center", va="center",
            transform=ax.transAxes,
            color=COLOR_AXIS, fontsize=9,
            zorder=1,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_axis_off()
        # tight=False: rect-границы держат полный canvas-bbox, иначе всё равно
        # обрезается до текста при empty-axes (matplotlib ≥3.7 quirk).
        return _figure_to_png(fig, tight=False)

    revenues = [float(p.revenue) for p in points]
    trend = [float(p.trend) for p in points]
    colors = [COLOR_PEAK if p.is_peak else COLOR_BAR for p in points]
    labels = [_format_month_short(p.month_start.month, p.month_start.year) for p in points]
    xs = list(range(len(points)))

    ax.bar(xs, revenues, color=colors, width=0.72, edgecolor="none")
    ax.plot(xs, trend, color=COLOR_TREND, linewidth=1.6, marker=None)

    # Прореживаем подписи оси X, чтобы при 24 точках они не наезжали.
    step = max(1, len(points) // 8)
    ax.set_xticks(xs[::step])
    ax.set_xticklabels(labels[::step], fontsize=8, color=COLOR_AXIS)
    ax.tick_params(axis="y", labelsize=8, colors=COLOR_AXIS)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.yaxis.grid(True, color=COLOR_GRID, linewidth=0.5)
    ax.set_axisbelow(True)

    return _figure_to_png(fig)


def render_sparkline(
    series: Sequence[Decimal],
    *,
    width_in: float = 1.6,
    height_in: float = 0.5,
    dpi: int = SPARKLINE_DPI,
    tone: str = "up",
) -> bytes:
    """Минималистичный sparkline для KPI-карточки (раздел G обложки).

    ``tone="up"`` — green stroke (положительный YoY), ``"down"`` — red.
    Без оси, без grid: рисует только линию по точкам ``series``. Пустой
    ``series`` или 1 точка → пустой PNG (шаблон не показывает sparkline).
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    ax.set_axis_off()

    if len(series) < 2:
        return _figure_to_png(fig, tight=False)

    color = "#0F8A5F" if tone == "up" else "#B42318"
    values = [float(v) for v in series]
    ax.plot(range(len(values)), values, color=color, linewidth=1.4)
    # Заливка под линией для приятного объёма.
    ax.fill_between(range(len(values)), values, min(values), color=color, alpha=0.12)
    return _figure_to_png(fig, tight=False)


def _figure_to_png(fig: Figure, *, tight: bool = True) -> bytes:
    """Сохраняет ``fig`` в PNG bytes и закрывает фигуру."""
    if tight:
        fig.tight_layout(pad=0.4)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight" if tight else None)
    plt.close(fig)
    return buf.getvalue()
