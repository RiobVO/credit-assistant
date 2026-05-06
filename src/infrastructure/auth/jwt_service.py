"""JWT issue/decode. HS256, access + refresh, без ротации refresh (см. spec 2.3).

Claim ``typ`` различает access ('access') и refresh ('refresh') — verify явно
проверяет тип, чтобы access не работал на refresh-endpoint и наоборот.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from jose import JWTError, jwt

TokenType = Literal["access", "refresh", "mfa_challenge"]
# `mfa_challenge` (Phase 5.B) — короткий 5-минутный JWT, выдаётся после успешной
# password-проверки если у аналитика включён real-TOTP. Verify TOTP-code'а потом
# проходит на /api/bank/auth/mfa/challenge, в обмен выдаются нормальные access+refresh.


class InvalidTokenError(Exception):
    """Токен невалиден: подпись/expired/wrong type."""


@dataclass(frozen=True, slots=True)
class TokenClaims:
    analyst_id: UUID
    token_type: TokenType
    jti: str
    expires_at: datetime


class JwtService:
    def __init__(
        self,
        secret: str,
        algorithm: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    def issue_access(self, analyst_id: UUID) -> str:
        return self._issue(analyst_id, "access", self._access_ttl)

    def issue_refresh(self, analyst_id: UUID) -> str:
        return self._issue(analyst_id, "refresh", self._refresh_ttl)

    def issue_mfa_challenge(self, analyst_id: UUID) -> str:
        """5-минутный challenge-token. Короткий TTL — защита от brute-force-флоу
        и retry-после-выхода. Срок не настраивается; жёстко прибит на 5 мин."""
        return self._issue(analyst_id, "mfa_challenge", timedelta(minutes=5))

    def decode(self, token: str, *, expected_type: TokenType) -> TokenClaims:
        try:
            payload: dict[str, Any] = jwt.decode(
                token, self._secret, algorithms=[self._algorithm]
            )
        except JWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        token_type = payload.get("typ")
        if token_type != expected_type:
            raise InvalidTokenError(
                f"Ожидался токен типа '{expected_type}', получен '{token_type}'"
            )

        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise InvalidTokenError("Отсутствует sub в payload")
        try:
            analyst_id = UUID(subject)
        except (TypeError, ValueError) as exc:
            raise InvalidTokenError(f"sub не UUID: {subject}") from exc

        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            raise InvalidTokenError("Отсутствует exp в payload")

        jti = payload.get("jti")
        if not isinstance(jti, str):
            raise InvalidTokenError("Отсутствует jti в payload")

        return TokenClaims(
            analyst_id=analyst_id,
            token_type=cast(TokenType, token_type),
            jti=jti,
            expires_at=datetime.fromtimestamp(exp, tz=UTC),
        )

    def _issue(self, analyst_id: UUID, token_type: TokenType, ttl: timedelta) -> str:
        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(analyst_id),
            "typ": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + ttl).timestamp()),
            "jti": uuid4().hex,
        }
        return cast(str, jwt.encode(payload, self._secret, algorithm=self._algorithm))
