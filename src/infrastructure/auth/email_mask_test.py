"""Unit для mask_email — audit_log PII redaction."""

from __future__ import annotations

from infrastructure.auth.email_mask import mask_email


def test_mask_email_keeps_first_two_chars() -> None:
    assert mask_email("ivanov@bank.uz") == "iv***@bank.uz"


def test_mask_email_short_local_part() -> None:
    assert mask_email("a@b.uz") == "a***@b.uz"


def test_mask_email_no_at_sign() -> None:
    assert mask_email("garbage") == "***"


def test_mask_email_empty() -> None:
    assert mask_email("") == "***"


def test_mask_email_preserves_full_domain() -> None:
    assert mask_email("admin@subdomain.bank.uz") == "ad***@subdomain.bank.uz"
