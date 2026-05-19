"""PdfMessages DTO: i18n-сообщения для PDF-досье (T0.4 / ADR-0015).

Чистый dataclass без I/O. Загрузка из ``config/pdf-i18n/<locale>.json`` живёт в
``infrastructure.i18n.pdf_messages.load_pdf_messages``. Этот модуль —
типизированный контракт между application/use_cases (RenderDossierPdf,
observations_builder) и infrastructure/reports/pdf (template_filters,
chart_renderer, pdf_renderer, templates/dossier.html).

Дизайн (ADR-0015 step 4): JSON keys плоские с dotted-namespaces
(``severity.critical``); loader группирует их в ``Mapping[str, str]`` поля
DTO. Месяцы — JSON arrays из 12 элементов → ``tuple[str, ...]``. Scalar
labels — отдельные поля. Помешшаемое placeholder'ом значение
(``observations_builder.head``, methodology paragraph) использует ``str.format``
с named kwargs.

Изменение JSON-ключей должно сопровождаться обновлением schema здесь +
loader-тестов: missing-key падает на ``IncompletePdfMessagesError``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdfMessages:
    """Все локализованные строки PDF-досье для одной локали.

    Группированные поля (``severity``, ``recommendation``, …) хранят
    ``Mapping[str, str]`` — ключи фиксированы доменом (FlagSeverity values,
    LegalForm names, evidence-key whitelist в ``pdf_renderer``). Loader
    валидирует обязательные subkeys; runtime KeyError = bug в JSON-конфиге.

    Месяцы — индексируются по ``month - 1`` (0..11). Format-placeholder'ы
    в строках типа ``obs_revenue_growth_head`` ожидают вызова ``.format(...)``
    в потребителе (observations_builder).
    """

    locale: str  # "ru" | "uz"

    # --- Cover hero ---
    cover_eyebrow_memorandum: str
    cover_eyebrow_summary: str
    cover_signals_fired: str
    cover_loan_request_label: str
    cover_loan_request_uzs_suffix: str
    currency_billion_short: str
    cover_loan_term_unit: str
    cover_loan_rate_suffix: str
    cover_data_as_of_label: str
    cover_methodology_label: str
    cover_methodology_evaluated_prefix: str
    cover_methodology_evaluated_suffix: str
    cover_observations_title: str
    cover_strengths_title: str
    cover_risks_title: str
    cover_strengths_empty: str
    cover_risks_empty: str

    # --- Section A — Identity ---
    section_a_title: str
    section_a_source: str
    identity_registered_at: str
    identity_business_age_label: str
    identity_business_age_since: str
    identity_region_label: str
    identity_okved_label: str
    identity_director_label: str
    identity_director_appointed: str
    identity_legal_address: str
    identity_main_activity: str
    identity_gnk_label: str

    # --- Section B — Financials ---
    section_b_title: str
    section_b_source: str
    financials_indicator: str
    financials_revenue: str
    financials_net_profit: str
    financials_taxes_paid: str
    financials_amounts_in_uzs_footnote: str
    financials_no_annual_disclaimer: str
    financials_no_data_hint: str

    # --- Section C — Monthly chart ---
    section_c_title: str
    section_c_source: str
    chart_alt_revenue: str
    chart_empty_no_monthly_title: str
    chart_empty_no_monthly_hint: str
    chart_empty_no_revenue_title: str
    chart_empty_no_revenue_hint: str

    # --- Section D — Counterparties ---
    section_d_title: str
    section_d_source: str
    counterparties_buyers: str
    counterparties_suppliers: str
    counterparties_table_counterparty: str
    counterparties_table_share: str
    counterparties_new_pill: str
    counterparties_no_buyers: str
    counterparties_no_suppliers: str

    # --- Section E — Tax discipline ---
    section_e_title: str
    section_e_source: str
    tax_summary_intro: str
    tax_delays_suffix: str
    tax_max_delay_prefix: str
    tax_max_delay_unit: str
    tax_penalties_total: str
    tax_freezes_12m: str
    tax_table_date: str
    tax_table_sum: str
    tax_table_delay: str
    tax_no_events_disclaimer: str

    # --- Section F — Signals ---
    section_f_title: str
    flag_rule_prefix: str
    flag_source_prefix: str
    flag_no_signals_disclaimer: str

    # --- Observations templates (consumed via str.format) ---
    obs_revenue_growth_head: str
    obs_revenue_growth_ctx_chain: str
    obs_revenue_growth_ctx_ltm_only: str
    obs_roe_head: str
    obs_roe_ctx_with_industry: str  # ADR-0024: «отрасль "{industry}" — UZ-медиана не публикуется»
    obs_roe_ctx_no_industry: str  # fallback если ОКЭД unknown в catalog
    obs_profit_head: str
    obs_profit_ctx_growth: str
    obs_profit_ctx_positive: str
    obs_no_debt_head: str
    obs_no_debt_ctx: str
    obs_debt_ratio_head: str
    obs_debt_ratio_ctx: str

    # --- Misc ---
    region_district_full: str
    methodology_label: str
    methodology_body: str
    disclaimer_label: str
    disclaimer_body: str
    running_head_inn_prefix: str

    # --- Grouped (loader склеивает dotted-keys в Mapping) ---
    recommendation: Mapping[str, str]
    severity: Mapping[str, str]
    signal_breakdown: Mapping[str, str]
    kpi_label: Mapping[str, str]
    legal_form_full: Mapping[str, str]
    legal_form_short: Mapping[str, str]
    evidence_label: Mapping[str, str]
    gnk_status: Mapping[str, str]
    gnk_source: Mapping[str, str]
    tax_episode: Mapping[str, str]
    business_age_year: Mapping[str, str]
    page_footer: Mapping[str, str]

    # --- Indexed by month - 1 (0..11) ---
    month_full: tuple[str, ...]
    month_short: tuple[str, ...]
