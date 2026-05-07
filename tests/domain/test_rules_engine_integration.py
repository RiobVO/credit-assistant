"""Integration: загружаем YAML → registry → run на синтетических снапшотах."""

from pathlib import Path

import pytest

from domain.services.scoring_service import Recommendation, ScoringService
from infrastructure.rules.registry_factory import load_registry
from tests.fixtures.synthetic_borrowers import (
    clean_borrower,
    critical_borrower,
    high_risk_borrower,
    loan_oversize_borrower,
    medium_risk_borrower,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = REPO_ROOT / "config" / "rules" / "v1_uz_msb.yaml"


@pytest.fixture(scope="module")
def registry():  # type: ignore[no-untyped-def]
    return load_registry(DEFAULT_YAML)


def test_clean_borrower_fires_no_flags(registry) -> None:  # type: ignore[no-untyped-def]
    flags = registry.run_all(clean_borrower())
    assert flags == []
    score = ScoringService().score(flags)
    assert score.recommendation == Recommendation.APPROVE
    assert score.score == 0


def test_medium_risk_fires_expected_rules(registry) -> None:  # type: ignore[no-untyped-def]
    flags = registry.run_all(medium_risk_borrower())
    rule_ids = {f.rule_id for f in flags}
    assert "SINGLE_BUYER_CONCENTRATION" in rule_ids
    assert "OKVED_CHANGED_12M" in rule_ids
    score = ScoringService().score(flags)
    assert score.recommendation in {Recommendation.APPROVE, Recommendation.REVIEW}


def test_high_risk_fires_multiple_rules_and_review(registry) -> None:  # type: ignore[no-untyped-def]
    flags = registry.run_all(high_risk_borrower())
    rule_ids = {f.rule_id for f in flags}
    assert "REVENUE_DROP_MOM_30" in rule_ids
    assert "TAX_PAYMENT_DELAYS" in rule_ids
    assert "NEW_COUNTERPARTY_LARGE_SHARE" in rule_ids
    score = ScoringService().score(flags)
    assert score.recommendation in {Recommendation.REVIEW, Recommendation.REJECT}


def test_critical_borrower_fires_vat_mismatch_and_shell(registry) -> None:  # type: ignore[no-untyped-def]
    flags = registry.run_all(critical_borrower())
    rule_ids = {f.rule_id for f in flags}
    assert "VAT_ESF_MISMATCH" in rule_ids
    assert "SHELL_COMPANY_PARTNERS" in rule_ids
    assert "TAX_PENALTIES_CURRENT_YEAR" in rule_ids
    assert "BANK_ACCOUNT_FROZEN_12M" in rule_ids
    score = ScoringService().score(flags)
    assert score.recommendation == Recommendation.REJECT


def test_loan_oversize_fires_loan_ratio_and_neg_profit(registry) -> None:  # type: ignore[no-untyped-def]
    flags = registry.run_all(loan_oversize_borrower())
    rule_ids = {f.rule_id for f in flags}
    assert "LOAN_TO_REVENUE_RATIO" in rule_ids
    assert "NEGATIVE_PROFIT_3Q" in rule_ids
    score = ScoringService().score(flags)
    assert score.recommendation in {Recommendation.REVIEW, Recommendation.REJECT}
