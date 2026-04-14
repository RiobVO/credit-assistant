# ADR 0001: Clean / Hexagonal architecture

- **Status**: Accepted
- **Date**: 2026-05-08
- **Phase**: 0

## Context

Продукт — инструмент банковской автоматизации. На горизонте 12-18 месяцев ожидаем:

- Несколько банков-клиентов, каждый со своей АБС и форматом данных.
- Рост числа адаптеров источников: Soliq Excel, ЭСФ JSON, банковский АБС, онлайн-ККМ, в будущем — официальный API Soliq.
- Bank Mode и Accountant Mode как два UI поверх одного бизнес-ядра.
- Регулярные правки в правилах оценки риска (17 red-flag правил с возможностью версионирования).

Если бизнес-логика смешается с I/O, кастомизация под каждого банка превратится в правки ядра, а тесты domain-логики потребуют поднятой БД.

## Decision

Применяем Clean Architecture с hexagonal вариацией:

- `domain/` — только pure-функции, entities, value objects, rules. Не импортирует ничего из `application/` или `infrastructure/`.
- `application/` — use cases. Зависит только от `domain/`. Определяет ports (абстрактные интерфейсы для внешнего мира).
- `infrastructure/` — реализации ports: персистентность, адаптеры источников, отчёты, auth.
- `interfaces/` — тонкий API/CLI слой, парсит запрос и зовёт use case.
- `config/` — настройки и DI-сборка.

DI делаем через FastAPI `Depends`. Внешний DI-контейнер не подключаем, пока сложность не оправдает overhead.

## Consequences

**Плюсы:**
- Тесты domain без БД, mock'ов и фикстур окружения.
- Новый банк = новый адаптер, ядро не трогаем.
- Чёткие границы → код-ревью легче (видно что именно меняется).

**Минусы:**
- Больше boilerplate на ранних стадиях (DTO, ports, мапперы).
- Соблазн «протащить инфра-объект через application» — нужно дисциплинировать ревью.

**Что сделать дальше (Phase 1):**
- Завести первые entities (`Borrower`, `FinancialReport`, `Invoice`, `RedFlag`) и value objects.
- Описать ports для адаптеров данных: `DataSourcePort`, `ReportPort`.

## References

- `PROJECT_BRIEF.md` Section 4 — диаграмма каталогов и ключевые правила.
- Eric Evans, *Domain-Driven Design*.
- Alistair Cockburn, *Hexagonal Architecture*.
