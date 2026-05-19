"""Observations builder: «Сильные стороны» + «Зоны риска» для cover PDF.

Phase 10 cover bottom half = executive summary rationale. Compliance officer
открывает PDF → сразу видит **почему** rule engine выдал именно эту
рекомендацию.

T0.4 / ADR-0015: head/num/ctx локализуются через ``PdfMessages``.
Format-placeholders (``{pct}``, ``{years}``, ...) резолвятся в этом
модуле — единственная точка для observations-related строк.

Структура:
* Strengths — derived из позитивных KPI / финансовых трендов (revenue growth,
  ROE>15, multi-year profit, low debt). До 3 пунктов, отсортированных
  by impact.
* Risks — top-3 сработавших red flags по severity (critical → high →
  medium → low), с маппингом ``rule_id → rule.name`` через ``RuleRegistry``.

Каждый Observation = ``head`` (заголовок с inline-числом) + ``num``
(KPI value для подсветки) + ``ctx`` (подпись с контекстом).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from application.dto.kpi_bundle import KpiBundle, KpiLevelTone
from application.dto.oked_benchmark import OkedBenchmarkBucket
from application.dto.pdf_messages import PdfMessages
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.red_flag import RedFlag
from domain.rules.rule import RuleRegistry, UnknownRuleError

MAX_OBSERVATIONS_PER_SIDE = 3


class BenchmarkLookup(Protocol):
    """ADR-0024 / Commit 3: structural protocol для DI каталога UZ-ОКЭД медиан.

    Observations_builder использует только метод ``by_oked_code``. Production —
    ``infrastructure.catalog.oked_benchmark.OkedBenchmarkCatalog``. Тесты могут
    реализовать минимальный stub без полного JSON loader'а.
    """

    def by_oked_code(self, code: str) -> OkedBenchmarkBucket | None: ...


@dataclass(frozen=True, slots=True)
class Observation:
    """Один пункт в strengths или risks колонке."""

    head: str  # «Рост выручки +18,2% YoY»
    num: str  # «+18,2%» — выделяется цветным mono
    ctx: str  # «3 года подряд: 12,5 → 14,8 → 17,6 млрд сум»


@dataclass(frozen=True, slots=True)
class Observations:
    strengths: tuple[Observation, ...]
    risks: tuple[Observation, ...]


def build_observations(
    snapshot: BorrowerSnapshot,
    kpis: KpiBundle,
    red_flags: tuple[RedFlag, ...],
    registry: RuleRegistry,
    messages: PdfMessages,
    benchmark_catalog: BenchmarkLookup | None = None,
) -> Observations:
    """Собирает strengths (по KPI/financials) и risks (top red flags).

    ADR-0024 / Commit 3: ``benchmark_catalog`` опционально инжектится для
    ROE-наблюдения. Если ``None`` — fallback на neutral строку без
    industry-имени (раньше PDF писал hardcoded «опт. торговли пищ. продуктами»
    — это был bug для всех ОКЭД ≠ G46.3).
    """
    return Observations(
        strengths=_build_strengths(snapshot, kpis, messages, benchmark_catalog),
        risks=_build_risks(red_flags, registry),
    )


# --- strengths ---------------------------------------------------------


def _build_strengths(
    snapshot: BorrowerSnapshot,
    kpis: KpiBundle,
    messages: PdfMessages,
    benchmark_catalog: BenchmarkLookup | None,
) -> tuple[Observation, ...]:
    """Кандидаты: revenue growth · strong ROE · positive profit · low debt.

    Возвращаем до 3 в порядке impact (revenue → ROE → profit → debt).
    Если ничего не tracked — пустой tuple (template отрисует empty state).
    """
    candidates: list[Observation] = []

    revenue_obs = _revenue_growth_observation(snapshot, kpis, messages)
    if revenue_obs:
        candidates.append(revenue_obs)

    roe_obs = _roe_observation(snapshot, kpis, messages, benchmark_catalog)
    if roe_obs:
        candidates.append(roe_obs)

    profit_obs = _net_profit_observation(snapshot, messages)
    if profit_obs:
        candidates.append(profit_obs)

    debt_obs = _debt_observation(kpis, messages)
    if debt_obs:
        candidates.append(debt_obs)

    return tuple(candidates[:MAX_OBSERVATIONS_PER_SIDE])


def _revenue_growth_observation(
    snapshot: BorrowerSnapshot, kpis: KpiBundle, messages: PdfMessages
) -> Observation | None:
    if kpis.revenue_ltm is None or kpis.revenue_ltm.yoy_pct is None:
        return None
    yoy = kpis.revenue_ltm.yoy_pct
    if yoy <= 0:
        return None
    pct_str = _format_pct(yoy)
    annuals = sorted(snapshot.annual_reports, key=lambda r: r.period.start)
    if len(annuals) >= 2:
        chain = " → ".join(_format_billion(r.revenue.amount) for r in annuals[-3:])
        ctx = messages.obs_revenue_growth_ctx_chain.format(years=len(annuals), chain=chain)
    else:
        ctx = messages.obs_revenue_growth_ctx_ltm_only
    return Observation(
        head=messages.obs_revenue_growth_head.format(pct=pct_str),
        num=f"+{pct_str}",
        ctx=ctx,
    )


def _roe_observation(
    snapshot: BorrowerSnapshot,
    kpis: KpiBundle,
    messages: PdfMessages,
    benchmark_catalog: BenchmarkLookup | None,
) -> Observation | None:
    if kpis.roe is None or kpis.roe.level_tone != KpiLevelTone.GOOD:
        return None
    roe_value = _format_pct(kpis.roe.value)
    ctx = _resolve_roe_ctx(snapshot, messages, benchmark_catalog)
    return Observation(
        head=messages.obs_roe_head.format(value=roe_value),
        num=roe_value,
        ctx=ctx,
    )


def _resolve_roe_ctx(
    snapshot: BorrowerSnapshot,
    messages: PdfMessages,
    benchmark_catalog: BenchmarkLookup | None,
) -> str:
    """ADR-0024: industry-aware ctx для ROE-наблюдения.

    Lookup ``snapshot.borrower.okved_main`` → bucket (section letter A/C/F/…).
    Если bucket найден — name_ru/name_uz зависит от locale messages.
    Catalog ``None`` или код unknown → neutral fallback без industry-имени.
    """
    if benchmark_catalog is None:
        return messages.obs_roe_ctx_no_industry
    code = snapshot.borrower.okved_main
    bucket = benchmark_catalog.by_oked_code(code) if code else None
    if bucket is None:
        return messages.obs_roe_ctx_no_industry
    industry_name = bucket.name_uz if messages.locale == "uz" else bucket.name_ru
    return messages.obs_roe_ctx_with_industry.format(industry=industry_name)


def _net_profit_observation(
    snapshot: BorrowerSnapshot, messages: PdfMessages
) -> Observation | None:
    annuals = sorted(snapshot.annual_reports, key=lambda r: r.period.start)
    if len(annuals) < 2:
        return None
    latest = annuals[-1]
    prior = annuals[-2]
    if latest.net_profit.amount <= 0:
        return None
    growth_ctx = ""
    if prior.net_profit.amount > 0:
        growth = (
            (latest.net_profit.amount - prior.net_profit.amount)
            / prior.net_profit.amount
            * Decimal(100)
        )
        if growth > 0:
            growth_ctx = messages.obs_profit_ctx_growth.format(
                pct=_format_pct(growth),
                prior_year=prior.period.start.year,
            )
    num = _format_billion(latest.net_profit.amount)
    year = latest.period.start.year
    return Observation(
        head=messages.obs_profit_head.format(num=num, year=year),
        num=num,
        ctx=growth_ctx or messages.obs_profit_ctx_positive.format(year=year),
    )


def _debt_observation(kpis: KpiBundle, messages: PdfMessages) -> Observation | None:
    if kpis.debt_to_ebit is None:
        return None
    if kpis.debt_to_ebit.value == Decimal(0):
        return Observation(
            head=messages.obs_no_debt_head,
            num="0",
            ctx=messages.obs_no_debt_ctx,
        )
    if kpis.debt_to_ebit.level_tone != KpiLevelTone.GOOD:
        return None
    ratio = _format_ratio(kpis.debt_to_ebit.value)
    return Observation(
        head=messages.obs_debt_ratio_head.format(ratio=ratio),
        num=ratio,
        ctx=messages.obs_debt_ratio_ctx,
    )


# --- risks -------------------------------------------------------------


def _build_risks(
    red_flags: tuple[RedFlag, ...], registry: RuleRegistry
) -> tuple[Observation, ...]:
    """Топ-N red flags по severity (critical → high → medium → low).

    Имя правила берётся из ``registry.by_id(rule_id).name`` — human-readable
    из YAML. ``RenderDossierPdf`` подменяет на ``name_uz`` через rule_names
    маппинг, но cover-observations всегда читают ``rule.name`` (RU canonical).
    UZ-локаль cover-risks использует ``rule_names[rule_id]`` через template,
    не через builder — упрощает зависимости.

    Числовое evidence (доля поставщика, % просрочки, и т.д.) идёт в ``num``
    и подсвечивается цветом в шаблоне.
    """
    if not red_flags:
        return ()

    by_severity = sorted(red_flags, key=lambda f: f.severity, reverse=True)
    out: list[Observation] = []
    for flag in by_severity[:MAX_OBSERVATIONS_PER_SIDE]:
        head = _resolve_rule_name(flag, registry)
        num = _format_evidence_num(flag.evidence)
        ctx = flag.message
        out.append(Observation(head=head, num=num, ctx=ctx))
    return tuple(out)


def _resolve_rule_name(flag: RedFlag, registry: RuleRegistry) -> str:
    """rule_id → rule.name из YAML; fallback на rule_id если не зарегистрирован."""
    try:
        rule = registry.by_id(flag.rule_id)
    except UnknownRuleError:
        return flag.rule_id
    return rule.name or flag.rule_id


def _format_evidence_num(evidence: dict[str, object]) -> str:
    """Первое числовое поле из evidence для подсветки. Пустой evidence → ''."""
    if not evidence:
        return ""
    value = next(iter(evidence.values()))
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


# --- formatters --------------------------------------------------------


def _format_pct(value: Decimal) -> str:
    """``18.2`` → ``18,2%``. Inputs уже в процентах (CA-043)."""
    return f"{value:.1f}".replace(".", ",") + "%"


def _format_billion(amount: Decimal) -> str:
    """``17_640_000_000`` → ``17,6``. UI довешивает «млрд сум»."""
    billions = amount / Decimal(1_000_000_000)
    return f"{billions:.1f}".replace(".", ",")


def _format_ratio(value: Decimal) -> str:
    """``1.85`` → ``1,85×``."""
    return f"{value:.2f}".replace(".", ",") + "×"
