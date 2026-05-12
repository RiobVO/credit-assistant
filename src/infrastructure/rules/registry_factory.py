"""Registry factory: маппит pure-функции из domain/rules на YAML-конфиг.

Добавление нового правила: 1) новая fn в domain/rules/<category>/<file>.py,
2) импорт сюда + строка в `CODE_RULES`, 3) запись в config/rules/v*.yaml.
Несостыковка id «code vs yaml» падает на старте через `load_registry`.
"""

from pathlib import Path

import yaml

from domain.rules.counterparty.circular_invoicing import circular_invoicing
from domain.rules.counterparty.new_counterparty_large_share import (
    new_counterparty_large_share,
)
from domain.rules.counterparty.shell_company_partners import shell_company_partners
from domain.rules.counterparty.single_buyer_concentration import (
    single_buyer_concentration,
)
from domain.rules.counterparty.single_supplier_concentration import (
    single_supplier_concentration,
)
from domain.rules.financial.low_margin_high_turnover import low_margin_high_turnover
from domain.rules.financial.negative_equity import negative_equity
from domain.rules.financial.negative_profit_3q import negative_profit_3q
from domain.rules.financial.revenue_drop_mom_30 import revenue_drop_mom_30
from domain.rules.financial.revenue_drop_yoy_50 import revenue_drop_yoy_50
from domain.rules.financial.vat_esf_mismatch import vat_esf_mismatch
from domain.rules.financial.vat_growth_no_revenue import vat_growth_no_revenue
from domain.rules.meta.insufficient_data import insufficient_data
from domain.rules.payment_discipline.bank_account_frozen_12m import (
    bank_account_frozen_12m,
)
from domain.rules.payment_discipline.tax_payment_delays import tax_payment_delays
from domain.rules.payment_discipline.tax_penalties_current_year import (
    tax_penalties_current_year,
)
from domain.rules.protocol import RuleFn
from domain.rules.rule import Rule, RuleRegistry
from domain.rules.structural.director_changed_6m import director_changed_6m
from domain.rules.structural.loan_to_revenue_ratio import loan_to_revenue_ratio
from domain.rules.structural.okved_changed_12m import okved_changed_12m
from infrastructure.rules.yaml_schema import RulesConfigYaml


class RuleConfigError(ValueError):
    """Конфиг YAML и код-реестр не сходятся."""


CODE_RULES: dict[str, RuleFn] = {
    "DIRECTOR_CHANGED_6M": director_changed_6m,
    "OKVED_CHANGED_12M": okved_changed_12m,
    "LOAN_TO_REVENUE_RATIO": loan_to_revenue_ratio,
    "REVENUE_DROP_MOM_30": revenue_drop_mom_30,
    "REVENUE_DROP_YOY_50": revenue_drop_yoy_50,
    "NEGATIVE_PROFIT_3Q": negative_profit_3q,
    "NEGATIVE_EQUITY": negative_equity,
    "VAT_GROWTH_NO_REVENUE": vat_growth_no_revenue,
    "VAT_ESF_MISMATCH": vat_esf_mismatch,
    "LOW_MARGIN_HIGH_TURNOVER": low_margin_high_turnover,
    "TAX_PAYMENT_DELAYS": tax_payment_delays,
    "BANK_ACCOUNT_FROZEN_12M": bank_account_frozen_12m,
    "TAX_PENALTIES_CURRENT_YEAR": tax_penalties_current_year,
    "SINGLE_BUYER_CONCENTRATION": single_buyer_concentration,
    "SINGLE_SUPPLIER_CONCENTRATION": single_supplier_concentration,
    "NEW_COUNTERPARTY_LARGE_SHARE": new_counterparty_large_share,
    "SHELL_COMPANY_PARTNERS": shell_company_partners,
    "CIRCULAR_INVOICING": circular_invoicing,
    "INSUFFICIENT_DATA": insufficient_data,
}


def load_registry(yaml_path: Path) -> RuleRegistry:
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    config = RulesConfigYaml.model_validate(raw)

    code_ids = set(CODE_RULES.keys())
    yaml_ids = {spec.id for spec in config.rules}

    missing_in_code = yaml_ids - code_ids
    if missing_in_code:
        raise RuleConfigError(
            f"YAML references rules not implemented in code: {sorted(missing_in_code)}",
        )
    missing_in_yaml = code_ids - yaml_ids
    if missing_in_yaml:
        raise RuleConfigError(
            f"Code defines rules not declared in YAML: {sorted(missing_in_yaml)}",
        )

    rules = [
        Rule(
            id=spec.id,
            version=config.version,
            severity=spec.severity,
            source=spec.source,
            category=spec.category,
            fn=CODE_RULES[spec.id],
            name=spec.name,
            name_uz=spec.name_uz,
        )
        for spec in config.rules
    ]
    return RuleRegistry(rules)
