"""Unit: JwtService — issue/decode для access и refresh, валидации."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from jose import jwt

from infrastructure.auth.jwt_service import InvalidTokenError, JwtService


def _service(secret: str = "test-secret") -> JwtService:
    return JwtService(
        secret=secret,
        algorithm="HS256",
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


def test_issue_and_decode_access_token() -> None:
    svc = _service()
    analyst_id = uuid4()
    token = svc.issue_access(analyst_id)

    claims = svc.decode(token, expected_type="access")

    assert claims.analyst_id == analyst_id
    assert claims.token_type == "access"
    assert claims.expires_at > datetime.now(tz=UTC)


def test_issue_refresh_has_longer_ttl_than_access() -> None:
    svc = _service()
    analyst_id = uuid4()
    access_claims = svc.decode(svc.issue_access(analyst_id), expected_type="access")
    refresh_claims = svc.decode(svc.issue_refresh(analyst_id), expected_type="refresh")
    assert refresh_claims.expires_at > access_claims.expires_at


def test_decode_rejects_wrong_token_type() -> None:
    """Access не может пройти где ожидается refresh — защита от подмены endpoints."""
    svc = _service()
    access = svc.issue_access(uuid4())
    with pytest.raises(InvalidTokenError):
        svc.decode(access, expected_type="refresh")


def test_decode_rejects_invalid_signature() -> None:
    svc_a = _service(secret="secret-a")
    svc_b = _service(secret="secret-b")
    token = svc_a.issue_access(uuid4())
    with pytest.raises(InvalidTokenError):
        svc_b.decode(token, expected_type="access")


def test_decode_rejects_expired_token() -> None:
    svc = JwtService(
        secret="s",
        algorithm="HS256",
        access_ttl=timedelta(seconds=-1),  # уже истёк
        refresh_ttl=timedelta(days=7),
    )
    token = svc.issue_access(uuid4())
    with pytest.raises(InvalidTokenError):
        svc.decode(token, expected_type="access")


def test_decode_rejects_garbage_token() -> None:
    svc = _service()
    with pytest.raises(InvalidTokenError):
        svc.decode("not.a.jwt", expected_type="access")


def test_decode_rejects_missing_jti() -> None:
    """Минимально кастомный payload без jti — должен отвергнуться."""
    payload = {
        "sub": str(uuid4()),
        "typ": "access",
        "iat": int(datetime.now(tz=UTC).timestamp()),
        "exp": int((datetime.now(tz=UTC) + timedelta(minutes=1)).timestamp()),
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        _service().decode(token, expected_type="access")


def test_jti_is_unique_per_token() -> None:
    svc = _service()
    analyst_id = uuid4()
    c1 = svc.decode(svc.issue_access(analyst_id), expected_type="access")
    c2 = svc.decode(svc.issue_access(analyst_id), expected_type="access")
    assert c1.jti != c2.jti
