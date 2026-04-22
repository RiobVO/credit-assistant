"""Unit: PasswordHasher — bcrypt round-trip."""

from __future__ import annotations

import pytest

from infrastructure.auth.password_hasher import PasswordHasher

# Bcrypt cost=4 для быстрых unit-тестов; в проде cost=12.
_FAST = PasswordHasher(rounds=4)


def test_hash_and_verify_round_trip() -> None:
    h = _FAST.hash("S3cret!")
    assert h != "S3cret!"
    assert _FAST.verify("S3cret!", h) is True


def test_verify_rejects_wrong_password() -> None:
    h = _FAST.hash("Correct")
    assert _FAST.verify("Wrong", h) is False


def test_hash_produces_unique_salts() -> None:
    """Bcrypt автоматически добавляет случайную соль — два hash'а от одного пароля отличаются."""
    h1 = _FAST.hash("same")
    h2 = _FAST.hash("same")
    assert h1 != h2
    assert _FAST.verify("same", h1) is True
    assert _FAST.verify("same", h2) is True


def test_verify_invalid_hash_format_raises() -> None:
    """Неверный формат hash — passlib бросает ValueError. Это явная ошибка вызывающего."""
    with pytest.raises(Exception):  # noqa: B017 — passlib бросает разные подклассы
        _FAST.verify("any", "not-a-bcrypt-hash")
