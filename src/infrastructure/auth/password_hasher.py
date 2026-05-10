"""Bcrypt-обёртка. Cost=12 — банковский стандарт.

Используем native ``bcrypt`` (не passlib): passlib 1.7.x не поддерживается
с 2020 и ломается на bcrypt 5.x (отсутствует ``__about__``). Native API
тонкий: ``hashpw`` + ``checkpw``.
"""

from __future__ import annotations

import bcrypt


class PasswordHasher:
    """Hash и verify паролей через bcrypt.

    Bcrypt cost=12 ≈ 250-300ms на современном CPU — приемлемо для banking auth
    и неприемлемо для brute force.
    """

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("ascii")

    def verify(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("ascii")
        )
