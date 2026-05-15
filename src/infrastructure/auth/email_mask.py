"""Audit-friendly email masking — local-part усечён до 2 символов.

Используется в audit_log payload, чтобы PII (полный email) не утекал в БД
(T1.3 / ADR-0017). Audit log остаётся debuggable (partial-match domain +
prefix), но full email reconstruction невозможен.

Контракт:
- "ivanov@bank.uz" → "iv***@bank.uz"
- "a@b.uz"         → "a***@b.uz"
- "garbage"        → "***" (нет @ — невалидный email)
- ""               → "***"
"""

from __future__ import annotations


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"
