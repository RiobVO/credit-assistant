# Uptime backfill

> Журнал ручных правок `system_uptime_day`. Только когда uptime collector
> не работал (dev stack выключен / миграция / disaster recovery) — не для
> косметики, не для prod-инцидентов.

## Зачем

`uptime_collector` (`src/infrastructure/jobs/uptime_collector.py`) пишет
worst-of-day status каждую минуту. Если API не запущен — row за этот день
отсутствует, UI /settings → «О приложении» показывает дыру в календаре
последних 30 дней. Banker не отличит дыру от реального outage'а.

## Когда backfill уместен

- dev/staging stack был выключен на ремонт, и дыра попадает в окно
  pre-demo / pilot trip (banker увидит пустой квадрат).
- Миграция с прежней инсталляции, до того как collector начал писать.

## Когда backfill не уместен

- Реальный production outage. Тогда строку должен записать **сам**
  collector — оставляем как есть, чтобы аудит был честным.
- Косметика без причины. Календарь — компонент `/settings`, не отчёт
  для регулятора.

## Скрипты

| Файл | Дата | Причина | Status |
|---|---|---|---|
| `scripts/backfill_uptime_20260516.sql` | 2026-05-16 | Dev-машина была выключена, не production outage; row нужен чтобы календарь /settings не показывал дыру в окне pre-demo trip | `down` |

## Применение

Все скрипты idempotent (`ON CONFLICT (day) DO NOTHING`). Повторный запуск
ничего не меняет.

```bash
# Через docker-compose (внутри контейнера postgres):
docker compose exec -T postgres psql -U credit -d credit_assistant \
    -c "$(cat scripts/backfill_uptime_<DATE>.sql)"

# С хоста (psql клиент, host:5433):
psql -h localhost -p 5433 -U credit -d credit_assistant \
    -f scripts/backfill_uptime_<DATE>.sql
```

## Verification

```sql
SELECT day, status FROM system_uptime_day
WHERE day BETWEEN CURRENT_DATE - 30 AND CURRENT_DATE
ORDER BY day DESC;
```

Не должно быть пропусков в continuous диапазоне (за исключением дней
ДО `first_seen_day` — это серые квадраты «до запуска инсталляции»).
