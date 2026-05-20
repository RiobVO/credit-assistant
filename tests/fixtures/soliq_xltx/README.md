# Soliq xltx fixtures

Реальные и анонимизированные выгрузки `my3.soliq.uz` для парсеров и integration-теста `tests/integration/real_xltx_test.py` (T0.1 Pre-Demo Roadmap).

## Соглашение об именах

| Суффикс | В git? | Назначение |
|---|---|---|
| `*_full.xltx` | **Нет** (gitignored через `tests/fixtures/**/*_full.*`) | Реальные выгрузки с моей ЭЦП. Локально, не уходит в репо. |
| `*_anon.xltx` | **Да** | Анонимизированные версии. Прогоняются в CI. |
| `*_sample.csv` / `*_sample.xltx` | Да | Синтетические минимальные fixtures для unit-тестов парсеров. |

## Workflow: положить новую real-выгрузку

1. Сохранить файл с ЭЦП-выгрузки в `tests/fixtures/soliq_xltx/<тип>_<период>_<inn>_full.xltx`.
   Пример: `vat_decl_q4_2025_201308534_full.xltx`.

2. Сгенерировать анонимизированную версию:

   ```bash
   python scripts/anonymize_xltx.py \
     tests/fixtures/soliq_xltx/vat_decl_q4_2025_201308534_full.xltx \
     tests/fixtures/soliq_xltx/vat_decl_q4_2025_anon.xltx
   ```

   Bulk-режим (для всех `*_full.xltx` в директории):

   ```bash
   python scripts/anonymize_xltx.py \
     --batch tests/fixtures/soliq_xltx/ \
     --output-dir tests/fixtures/soliq_xltx/
   ```

   Существующие `*_anon.xltx` пропускаются — добавь `--force` для overwrite.
   В batch-режиме `*_anon.xltx` имена строятся через детерминированную подмену
   9/14-digit INN в стеме (защита от collision'ов: `form1_2025_<inn>_full.xltx`
   с разными INN дают разные anon-имена).

3. Прогнать тест (Docker не нужен — тест лежит в `tests/parsers/`, не `tests/integration/`):

   ```bash
   uv run python -m pytest tests/parsers/real_xltx_test.py -v
   ```

   Ожидание:
   - `*_full` и `*_anon` файлы — оба должны парситься без `parse_warnings`.
   - `PROFIT_TAX` файлы — `xfailed` (parser в T2.3).
   - Если детектор вернул `UNKNOWN` — `fail`. Либо файл битый, либо нужен новый sentinel в `format_detector.py`.

4. Закоммитить только `*_anon.xltx` (`*_full.*` автоматически проигнорируется).

## Что anonymizer замазывает

- **ИНН** (9 / 14 подряд цифр) → детерминированный hash той же длины. Один и тот же ИНН → один и тот же anon (сохраняет cross-file references).
- **Имена компаний** (ООО / ОАО / АО / MCHJ / ХК / ХТ / ХУСУСИЙ) → `ОБЕЗЛИЧЕНО NNN`.
- **Суммы** (numeric > 1000) → `value / 10`. Порядок величин сохраняется (для KPI-smoke), реальные цифры не утекают.
- **Формулы** не трогаются — пересчитаются автоматически после `/10`.

## Что НЕ замазывается (намеренно)

- Sentinel-строки формата ("Расчёт НДС", "Бухгалтерский баланс" и т.п.) — без них `format_detector` вернёт `UNKNOWN` и тест упадёт.
- Даты, периоды, ОКВЭДы — публичная справочная информация.
- Структура листов (`list01..list15`) — определяет тип файла.

Если после прогона `parse_warnings != []` на anon-файле, но на оригинале их не было — anonymizer что-то сломал. Уменьшить `_AMOUNT_THRESHOLD` или сузить `_COMPANY_PATTERN` в `scripts/anonymize_xltx.py`.

## ⚠ Trade-off: rule-engine на anon-данных

`/10` сохраняет **пропорции** (debt/equity, ROE, margins, growth rates) — KPI работают.
Абсолютные пороги — **нет**. Правила вида «revenue < 100M UZS critical» сработают иначе на anon.

Acceptance T0.1 (`parse_warnings == []`) этим не затронут — парсер на абсолютные суммы не смотрит. Но при добавлении rule-engine тестов: absolute-threshold правила тестируй на synthetic fixtures из `tests/fixtures/synthetic_borrowers.py`, не на `*_anon.xltx`.
