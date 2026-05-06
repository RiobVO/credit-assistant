"""TOTP-сервис: RFC 6238 секреты + verify + recovery backup-codes.

Используется ``pyotp`` для core-логики (генерация base32 secret, TOTP-вычисление
по time-window, verify с tolerance ±1 step = ±30s).

Recovery-коды: 10 одноразовых 8-значных строк (буквы+цифры). Хранятся в БД
bcrypt-хешами (одноразовый стек: при использовании хеш удаляется из массива).
Plain выдаются user'у один раз сразу после enrollment'а.
"""

from __future__ import annotations

import secrets
import string
from collections.abc import Callable
from dataclasses import dataclass

import pyotp

from infrastructure.auth.password_hasher import PasswordHasher

# Issuer-строка в provisioning URI — попадёт в название записи в Authenticator app.
# Конкретный бренд аналитика читается из brand-config, но в TOTP issuer мы кладём
# generic «Credit Assistant» — TOTP app'ы плохо рендерят русские/branded строки.
_ISSUER = "Credit Assistant"

_BACKUP_CODES_COUNT = 10
_BACKUP_CODE_ALPHABET = string.ascii_uppercase + string.digits


@dataclass(frozen=True, slots=True)
class EnrollmentArtifacts:
    """Что возвращается на /enroll/start: secret (показать в UI как fallback)
    + provisioning_uri (фронт делает QR-код). Backup-codes генерятся не здесь,
    а после verify (пока user не ввёл первый TOTP — enrollment не закреплён)."""

    secret: str
    provisioning_uri: str


def generate_enrollment(
    email: str, *, _suffix_factory: "Callable[[], str] | None" = None
) -> EnrollmentArtifacts:
    """Генерирует свежий TOTP secret + provisioning URI.

    Account name в URI — это ``localpart+SUFFIX@domain`` (RFC 5233 subaddress),
    где SUFFIX — короткий случайный hex. Это обходит quirk Microsoft Authenticator
    + других apps c iCloud/Google-Account backup: они дедуплят добавленные
    аккаунты по подстроке-email, а не по полному label. Если local-part
    каждое re-enrollment отличается — MS Auth добавит как новый аккаунт без
    диалога «уже существует».

    Real-world сценарий: аналитик потерял телефон → IT отключает 2FA через
    admin-flow → аналитик заново enroll'ится с нового телефона. Старая
    запись в его MS-account-cloud не помешает scan'у нового QR.

    Тестируемость: ``_suffix_factory`` инжектируется (для детерминизма в тестах);
    в production — ``secrets.token_hex(3)`` → 6-char hex (~16M вариантов).
    """
    secret = pyotp.random_base32()
    suffix = (_suffix_factory or (lambda: secrets.token_hex(3)))()
    if "@" in email:
        local, _, domain = email.partition("@")
        account_name = f"{local}+{suffix}@{domain}"
    else:
        # email без @ — corner case (CLI seed может прислать non-email)
        account_name = f"{email}+{suffix}"
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=account_name, issuer_name=_ISSUER
    )
    return EnrollmentArtifacts(secret=secret, provisioning_uri=uri)


def verify_totp(secret: str, code: str) -> bool:
    """Verify 6-digit TOTP code against secret. ``valid_window=1`` allows ±30s
    clock skew (standard practice for TOTP UX)."""
    if not code or not code.strip().isdigit() or len(code.strip()) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code.strip(), valid_window=1))


def generate_backup_codes() -> list[str]:
    """10 одноразовых 8-значных кодов из A-Z0-9. Plain — выдаются user'у только
    один раз после enrollment'а; в БД идут хешированные."""
    return [
        "".join(secrets.choice(_BACKUP_CODE_ALPHABET) for _ in range(8))
        for _ in range(_BACKUP_CODES_COUNT)
    ]


def hash_backup_codes(codes: list[str], hasher: PasswordHasher) -> list[str]:
    """bcrypt-хешируем каждый код (тот же hasher, что для паролей — single ratchet)."""
    return [hasher.hash(c) for c in codes]


def consume_backup_code(
    hashed_codes: list[str], submitted: str, hasher: PasswordHasher
) -> list[str] | None:
    """Если submitted matches один из hashed_codes — возвращает новый список
    без использованного хеша. Иначе None (no match).

    Каждый код одноразовый: после использования хеш удаляется из массива.
    """
    normalized = submitted.strip().upper().replace(" ", "")
    if not normalized:
        return None
    for idx, h in enumerate(hashed_codes):
        if hasher.verify(normalized, h):
            return [*hashed_codes[:idx], *hashed_codes[idx + 1 :]]
    return None
