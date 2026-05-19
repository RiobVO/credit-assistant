"""FX_MISMATCH_HIGH: валютный заём против рублёво-сумовой выручки (ADR-0024)."""

# RULE_SOURCE: World Bank Group, Financial Sector Assessment Program — Uzbekistan
#   (FSAP 2025) — банковский сектор УзР, 44% МСБ-портфеля в иностранной валюте
#   при выручке заёмщиков преимущественно в UZS. Источник классифицирован как
#   HIGH risk indicator (open FX exposure → currency mismatch default).
# CONFIDENCE: HIGH (multilateral / IMF-WB joint assessment)
# VALIDATED_BY: []

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence
from domain.value_objects.money import Currency


def fx_mismatch(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает когда валюта займа ≠ UZS, а выручка по latest_annual — UZS.

    * `loan_request is None` → None (правило применимо только при заявке)
    * Нет `annual_reports` → None (нет revenue-базы для сравнения)
    * Currency займа == Currency выручки → None (FX-mismatch отсутствует)
    * Currency займа != Currency выручки → fires high-severity

    Логика максимально консервативная — сравниваем по latest_annual.revenue,
    а не по среднему. FX-risk одной фазой остаётся FX-risk: рост курса
    девальвирует UZS-выручку, при этом обслуживание валютного долга
    дорожает соразмерно. Murodov O.J. 2025 (Tashkent State University of
    Economics) фиксирует это как доминирующий драйвер дефолтов в UZ-cotton.
    """
    loan = snapshot.loan_request
    if loan is None:
        return None
    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)

    loan_currency = loan.amount.currency
    revenue_currency = latest.revenue.currency
    if loan_currency == revenue_currency:
        return None

    # Сообщения локализованы — RU для аналитика, UZ для PDF-uz.
    loan_ccy_name = loan_currency.value
    rev_ccy_name = revenue_currency.value
    fires_only_when_uzs_revenue = revenue_currency == Currency.UZS
    if fires_only_when_uzs_revenue:
        msg_ru = (
            f"Заём в {loan_ccy_name}, выручка в {rev_ccy_name} — "
            "валютный риск (open FX exposure)"
        )
        msg_uz = (
            f"Kredit {loan_ccy_name}, tushum {rev_ccy_name} — "
            "valyuta tavakkalligi (open FX exposure)"
        )
    else:
        msg_ru = (
            f"Валюта займа ({loan_ccy_name}) не совпадает с валютой выручки "
            f"({rev_ccy_name}) — валютный риск"
        )
        msg_uz = (
            f"Kredit valyutasi ({loan_ccy_name}) tushum valyutasi "
            f"({rev_ccy_name}) bilan mos kelmaydi — valyuta tavakkalligi"
        )

    return FiringEvidence(
        message=msg_ru,
        message_uz=msg_uz,
        evidence={
            "loan_currency": loan_ccy_name,
            "revenue_currency": rev_ccy_name,
            "loan_amount": str(loan.amount.amount),
        },
    )
