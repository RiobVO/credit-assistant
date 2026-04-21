# ADR 0008: PDF rendering stack — WeasyPrint + Jinja2 + matplotlib

- **Status**: Accepted
- **Date**: 2026-05-10
- **Phase**: 3 (подфаза 3.C)

## Context

Phase 3.C активирует кнопку «Скачать PDF» на экране досье
(`/dossier/[id]`). Нужен production-grade рендерер, который:

- умеет HTML→PDF с CSS Paged Media (A4, поля, running footer);
- корректно показывает кириллицу (русский UI обязателен) и узбекский Cyrillic;
- встраивает динамические matplotlib-чарты (раздел C, 24 мес выручки);
- работает on-prem без интернета (banking deploy, ADR 0002 — никаких
  cloud-only зависимостей);
- укладывается в Python 3.12 + FastAPI стек (ADR 0002).

## Decision

Стек: **WeasyPrint 68 + Jinja2 3.1 + matplotlib 3.10**.

```
DossierPdfBundle ──► Jinja2 (templates/dossier.html, 9 фильтров)
                         │
                         ▼
                       HTML
                         │
                         ▼
                   WeasyPrint write_pdf()  ──►  bytes
                         ▲
                         │
matplotlib ─► PNG ──► base64 data-URI ─┘
```

- **WeasyPrint** — единственный python-движок с зрелой поддержкой CSS
  Paged Media, `@page`-директив (running footer), counters
  (нумерация страниц), поддерживает кастомные шрифты через `@font-face`.
  С версии 60 PDF собирается через pure-python `pydyf` (без Cairo) —
  размер deploy уменьшился, но Pango/HarfBuzz для shaping текста всё
  ещё нужны нативно.
- **Jinja2** — стандарт для шаблонов в Python-стеке, поддержка кастомных
  фильтров (см. `template_filters.py`) и autoescape для безопасного
  рендера user-controlled данных.
- **matplotlib** — генератор PNG для чартов. PNG встраиваем в HTML
  через base64 `data-URI` — WeasyPrint не делает HTTP-запросы за
  ресурсами в банковском контуре, всё inline.

## Deployment: Docker-only

WeasyPrint требует libpango/libharfbuzz/libfontconfig нативно. На
Windows-хосте без GTK runtime импорт падает с
`OSError: cannot load library 'libgobject-2.0-0'`. Поэтому backend
переехал в compose-сервис `api` (`Dockerfile` на `python:3.12-slim` +
`apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b
libfontconfig1`):

- **Dev на Windows** = `docker compose up -d api` (hot reload через
  rebuild, не volume mount — устроит итерационный цикл; добавим mount
  при необходимости).
- **Prod (банк on-prem)** = тот же Dockerfile в k8s/swarm/standalone
  Docker. Linux + libpango ставятся уже в base image, никаких ручных
  GTK-installer'ов на серверах банка.

**Почему не альтернативы:**

| Вариант | Отвергнут потому что |
|---|---|
| ReportLab pure-Python | Нет HTML/CSS — вёрстка программная; mockup пришлось бы переписывать с нуля; визуально шаг назад от экрана |
| Playwright/Chromium | +200 МБ Chromium в банковском контуре; ещё один runtime для аудита; CSS Paged Media работает иначе |
| wkhtmltopdf | Deprecated с 2023, security advisories; Qt-based, тяжёлый |
| GTK3 runtime для Windows-uvicorn | Один раз решает проблему dev, но prod всё равно Linux — лучше унифицировать сразу |
| Отдельный pdf-микросервис | Over-engineering для MSB MVP — добавляет HTTP-hop ради одной фичи |

## Endpoint contract

`GET /api/dossier/{dossier_id}/pdf`:

- **200**: `Content-Type: application/pdf`, `Content-Disposition:
  attachment; filename="BR-XXXX.pdf"` (XXXX — первые 4 hex uuid).
  Body — bytes готового PDF.
- **404**: dossier не найден (тот же путь, что и read endpoint).
- **422**: путь не парсится в UUID.
- **503**: WeasyPrint не смог импортировать GTK (защитная сетка для
  случаев, когда кто-то запустит uvicorn вне контейнера).

Use case `RenderDossierPdf` оборачивает sync `port.render` в
`asyncio.to_thread`, чтобы не блокировать event loop FastAPI.

## Шрифты

`font-family: "Inter", "DejaVu Sans", sans-serif` — fallback chain.
**v1 шаблон работает на DejaVu Sans** (системный в Debian-base, полная
поддержка кириллицы). Inter подключим позже через bundle TTF в
`infrastructure/reports/pdf/fonts/` — нужен FontConfiguration, ~600 KB
в репо. Фиксируем как **TODO[CA-010]**: некритично для DoD Phase 3.C,
улучшение типографики.

## Degraded states

Шаблон умеет ноль данных без падений:

- Пустой `monthly_revenue_24m` → `chart_renderer` рисует placeholder
  PNG с подписью «Нет данных для построения графика».
- KPI null → карточка показывает «—» + «Нет данных для расчёта».
- Empty `red_flags` → блок «Сигналы не сработали».
- Missing `loan_request` → строка subtitle без блока заявки.
- Empty `top_buyers`/`top_suppliers` → раздел D показывает disclaimer.

Принципиальная позиция: **ничего не выдумываем**. Если данных нет —
говорим прямо.

## Testing strategy

- **Unit**: 21 тест на фильтры (форматирование, edge cases) + 3 теста
  на render шаблона (Jinja-only, без PDF) + 5 тестов chart_renderer
  (PNG magic + размер + degraded) + 11 тестов aggregator/use case.
  Все в `pytest -m "not integration"`, запускаются локально на
  Windows-uvicorn без Docker.
- **Integration**: 5 тестов с реальным PDF-рендером (helper `_make_bundle`
  + endpoint POST→GET). `pytest.mark.integration +
  pytest.mark.skipif(sys.platform == "win32")` — на Windows-хосте
  скипаются автоматически. Запуск: `docker compose up -d` →
  `pytest -m integration` против real Postgres + WeasyPrint в Linux
  контейнере (см. `tests/integration/conftest.py`).

## Rollout & migration

- Существующая локальная разработка через `uv run uvicorn` остаётся
  валидной для не-PDF фич. Frontend ходит на `localhost:8000`
  одинаково, кто бы там ни слушал — uvicorn локально или compose api.
- Конфликт портов: пока активен compose api, локальный uvicorn нельзя
  поднять одновременно. Документируем в README.

## Trade-offs accepted

- Зависимость от Docker для PDF-разработки — приемлемо: prod-стек
  идентичный, экономит «двойной maintenance» Windows + Linux setups.
- DejaVu Sans вместо Inter в v1 PDF — приемлемо: PDF читается, дизайн
  совпадает по структуре с экраном (разница только в гарнитуре).
- matplotlib + WeasyPrint импортятся 200-300 мс на cold start —
  приемлемо: первый PDF-запрос держит в `lru_cache` Jinja2 Environment
  + matplotlib backend; следующие запросы используют разогретое.

## Future work

- **TODO[CA-010]**: bundle Inter TTF (400/500/600/700) + JetBrains Mono
  (500/600) в `fonts/`, прописать `@font-face`. Тогда PDF и экран
  выглядят одной семьёй.
- Шаблон может разрастись на partials по мере добавления секций H+
  (история заявок, сравнение с прошлым досье).
- В Phase 4 Bank Mode — водяной знак «Только для внутреннего
  пользования банка X» через `@page background-image` или CSS
  pseudo-element.

## References

- WeasyPrint docs: https://doc.courtbouillon.org/weasyprint/stable/
- Jinja2 + WeasyPrint integration patterns
- ADR 0002 (tech stack), 0003 (rules engine), 0007 (score mapping) —
  контекст для дизайн-решений в этом ADR
