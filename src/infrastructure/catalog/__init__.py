"""Catalog loaders: reference data (OKVED, exchange rates, ...) из ``config/``.

Зеркалит ``infrastructure.brand`` pattern — JSON в ``config/<topic>/``,
loader читает at startup, exposes typed DTO. Frontend получает то же
содержимое через ``GET /api/system/<topic>`` endpoints.
"""
