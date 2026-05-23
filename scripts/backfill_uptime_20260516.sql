-- Backfill 2026-05-16 в system_uptime_day.
--
-- Контекст: dev-машина была выключена 2026-05-16 — pre-pilot пауза, не
-- production outage. Uptime collector работает только в running api, поэтому
-- row за этот день отсутствует. UI /settings → «О приложении» рендерит
-- календарь 30 квадратов и без backfill показывает дыру между 15 и 17.
--
-- Status выставлен `down` — это честнее, чем `ok`: API в эти сутки не
-- отвечал, хотя причина — плановое выключение dev-стека, не инцидент prod.
-- note хранит человекочитаемое объяснение для будущего forensics.
--
-- Idempotent: ON CONFLICT DO NOTHING. Повторный запуск ничего не меняет.
--
-- Применение:
--   docker compose exec -T postgres psql -U credit -d credit_assistant \
--     -f /app/scripts/backfill_uptime_20260516.sql
-- или (с хоста, через psql клиент):
--   psql -h localhost -p 5433 -U credit -d credit_assistant \
--     -f scripts/backfill_uptime_20260516.sql

INSERT INTO system_uptime_day (day, status, first_seen_at, last_seen_at, note)
VALUES (
    DATE '2026-05-16',
    'down',
    TIMESTAMPTZ '2026-05-16 00:00:00+00',
    TIMESTAMPTZ '2026-05-16 23:59:59+00',
    'dev stack выключен (плановая пауза); not a production outage'
)
ON CONFLICT (day) DO NOTHING;
