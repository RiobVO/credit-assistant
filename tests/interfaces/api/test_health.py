"""Smoke-тест health-эндпоинта — доказательство, что приложение собирается и отвечает."""

from httpx import ASGITransport, AsyncClient

from config.constants import APP_VERSION
from interfaces.api.app import create_app


async def test_health_returns_ok_status_and_version() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "version": APP_VERSION}
