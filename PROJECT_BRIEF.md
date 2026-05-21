# Claude Code Engineering Brief: Credit Assistant MSB

> **Хранить как `PROJECT_BRIEF.md` в корне проекта.**
> Этот документ — единственный источник правды для разработки. Перед каждой большой задачей Claude Code обязан перечитать этот файл.

---

## 1. Product Mission

Build a production-grade internal tool for **mid-tier Uzbek commercial banks** that automates collection and pre-processing of MSB (small/medium business) borrower data for credit underwriting.

**Замена**: 2-3 hours of manual analyst work per borrower → **8-10 minutes** automated.
**Целевой клиент**: Hamkorbank, SQB, Uzpromstroybank, Trastbank, Anor Bank, Asia Alliance, Bereke, Davr Bank, Halk Bank, Mikrokreditbank — все, кто отстаёт от TBC/Kapitalbank в digitalization.
**Регуляторное окно**: ЦБ РУз внедряет Базель III, ужесточает DTI-требования, требует 3-летнюю историю заёмщика. Банки **обязаны** улучшать методики риск-анализа.
**Конкурентный ландшафт**: TBC уже автоматизировал свой МСБ-кредитный pipeline. Mid-tier банки теряют клиентов. Это твоё окно 12-18 месяцев.

---

## 2. Two Operating Modes (CRITICAL)

Продукт имеет **два режима работы** в едином коде:

### Mode A: BANK MODE (основной revenue)
- Пользователь — кредитный аналитик банка
- Доступ через корпоративную сеть банка (on-premise deployment)
- Аналитик вводит ИНН заёмщика → получает полное досье + красные флаги + scoring
- Output: PDF/HTML отчёт для прикрепления в АБС банка
- Authorization: банковский SSO (mock в POC, real LDAP/OAuth в production)

### Mode B: ACCOUNTANT MODE (валидация + дополнительная демо)
- Пользователь — бухгалтер (use-case: папа-главбух)
- Доступ локально на Mac/Win бухгалтера
- Бухгалтер загружает выгрузки своих фирм → видит, **как банк их увидел бы**
- Используется для:
  - **Валидации логики** ("я знаю эту фирму, проверим — правильно ли инструмент её оценил")
  - **Бесплатной маркетинговой демо** ("пап, покажи это знакомым предпринимателям, они увидят, как банк их оценивает")
- Authorization: простой login/password, локально

**Архитектура должна разделять эти режимы как два UI поверх одного бизнес-ядра.**

---

## 3. Tech Stack (final, no debate)

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI (async, OpenAPI docs out of the box)
- **ORM**: SQLAlchemy 2.0 (async)
- **DB**: PostgreSQL 16 (in production), SQLite (dev/POC)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Auth**: python-jose (JWT), passlib (bcrypt)
- **Background jobs**: ARQ (Redis-based, simpler than Celery)
- **HTTP client**: httpx (async)
- **Excel parsing**: openpyxl + pandas
- **PDF generation**: WeasyPrint (HTML→PDF, поддерживает кириллицу)
- **Testing**: pytest + pytest-asyncio + httpx (test client)
- **Linting**: ruff + mypy --strict

### Frontend
- **Framework**: Next.js 15 (App Router) + React 19
- **Language**: TypeScript strict mode
- **UI library**: shadcn/ui + Tailwind CSS 4
- **Charts**: Recharts (для графиков оборотов)
- **State**: React Query (TanStack Query) для server state, zustand для local UI
- **Forms**: react-hook-form + zod validation
- **Tables**: TanStack Table
- **i18n**: next-intl (русский + узбекский — банки в UZ работают на обоих)

### DevOps
- **Containerization**: Docker + Docker Compose
- **Reverse proxy**: Caddy 2 (HTTPS из коробки)
- **CI/CD**: GitHub Actions
- **Logging**: structlog (JSON-формат)
- **Monitoring**: Prometheus + Grafana (для production, не POC)
- **Secrets**: .env через python-dotenv, в production — банковский Vault

### Why this stack
- **Python+FastAPI**: лучший баланс скорости разработки и production-готовности; AI-orchestration работает с ним идеально
- **Next.js+TypeScript**: production-grade UI без выдумывания; банки видят такой стек у TBC/Kapitalbank, не отпугнёт
- **PostgreSQL**: банковский стандарт; SQLite в POC, чтобы не тратить время на setup
- **shadcn/ui**: профессиональный вид сразу, без "AI-design"
- **Caddy**: автоматический HTTPS, что важно для on-premise банка

**ANTIPATTERNS — НЕ ИСПОЛЬЗОВАТЬ:**
- ❌ Django (тяжёлый, синхронный, overkill)
- ❌ Flask (старая школа, нет async, нет валидации)
- ❌ MongoDB (банкам нужны транзакции и ACID)
- ❌ Vue/Angular (банки UZ привыкли к React-стеку)
- ❌ Создавать UI с нуля без shadcn (потратишь дни на компоненты)
- ❌ Selenium/Puppeteer для парсинга Soliq (нелегально без согласия владельца)

---

## 4. Architecture: Clean + Hexagonal

```
src/
├── domain/                 # Pure business logic, no I/O
│   ├── entities/           # Borrower, FinancialReport, Invoice, RedFlag
│   ├── value_objects/      # INN, Money, DateRange, FlagSeverity
│   ├── rules/              # 17 red-flag rules (versionable, configurable)
│   └── services/           # ScoringService, DossierService
│
├── application/            # Use cases, orchestration
│   ├── use_cases/          # CollectDossier, RunRedFlags, GenerateReport
│   ├── dto/                # Request/Response models
│   └── ports/              # Abstract interfaces (DataSourcePort, ReportPort)
│
├── infrastructure/         # I/O implementations
│   ├── adapters/
│   │   ├── soliq_excel/    # Parse Soliq Excel exports
│   │   ├── esf_json/       # Parse ESF JSON exports
│   │   ├── manual_input/   # Manual data entry (POC fallback)
│   │   └── tax_calendar/   # Hardcoded tax payment dates UZ
│   ├── persistence/        # SQLAlchemy models, repositories
│   ├── reports/            # PDF/HTML generators
│   └── auth/               # JWT, password hashing
│
├── interfaces/             # API + UI entry points
│   ├── api/
│   │   ├── bank/           # Bank mode endpoints
│   │   ├── accountant/     # Accountant mode endpoints
│   │   └── shared/         # Common endpoints
│   └── cli/                # Admin CLI for ops
│
└── config/                 # Settings, DI container
```

**Key architectural rules:**
- `domain/` НЕ импортирует ничего из `infrastructure/` или `application/`
- `application/` импортирует только из `domain/` и определяет интерфейсы (ports)
- `infrastructure/` имплементирует интерфейсы из `application/ports/`
- `interfaces/` — тонкий слой, только парсинг запроса и вызов use case
- DI через `dependency-injector` или вручную через FastAPI Depends

**Why Clean Architecture здесь:**
- Каждый банк попросит свою customization → менять надо только adapters, не ядро
- Тесты domain-логики возможны без БД и API
- Через 6 месяцев новый банк → новый adapter, остальное переиспользуется

---

## 5. Red-Flag Rules Engine (HEART OF PRODUCT)

Реализовать как **rules engine** с YAML-конфигурацией, чтобы можно было добавлять/убирать/настраивать правила без правки кода.

### Структура правила
```yaml
# config/rules/v1_uz_msb.yaml
rules:
  - id: REVENUE_DROP_MOM_30
    name: "Падение выручки месяц-к-месяцу >30%"
    category: financial
    severity: high
    source: "ЦБ РУз положение №27-п, п.4.5; Базель III IRB approach"
    formula: "revenue_mom_pct < -0.30 for 2 consecutive months"
    rationale: "Резкое падение выручки — сильнейший предиктор дефолта на горизонте 6 мес"

  - id: SINGLE_BUYER_CONCENTRATION
    name: "Концентрация >70% выручки на одном покупателе"
    category: counterparty
    severity: medium
    source: "Базель III concentration risk; внутренние методики Kapitalbank"
    formula: "max_buyer_revenue_share > 0.70"
    rationale: "Высокий риск потери всего бизнеса при уходе клиента"

  - id: NEW_COUNTERPARTY_LARGE_SHARE
    name: "Новый контрагент >30% оборота за 3 мес"
    category: counterparty
    severity: high
    source: "Group-IB Uzbekistan fraud report 2024-2025"
    formula: "counterparties_registered_lt_180d_share > 0.30"
    rationale: "Типичная схема накрутки оборотов перед получением кредита"

  - id: VAT_ESF_MISMATCH
    name: "Разрыв декларация НДС vs ЭСФ >15%"
    category: financial
    severity: critical
    source: "НК РУз ст. 256; Soliq внутренние методики"
    formula: "abs(vat_declared - sum_esf_amounts) / vat_declared > 0.15"
    rationale: "Прямое расхождение декларации с фактическими ЭСФ — признак фиктивной отчётности"

  # ... остальные 13 правил из PROJECT_BRIEF section 7
```

### Movement Rules — must implement all 17:

**Финансовые (Financial):**
1. `REVENUE_DROP_MOM_30`: Падение оборота >30% МоМ два периода подряд
2. `REVENUE_DROP_YOY_50`: Падение оборота >50% YоY
3. `NEGATIVE_PROFIT_3Q`: Чистая прибыль ≤0 три квартала подряд
4. `VAT_GROWTH_NO_REVENUE`: Рост НДС-обязательств без роста выручки
5. `VAT_ESF_MISMATCH`: Разрыв НДС-декларация vs ЭСФ >15%
6. `LOW_MARGIN_HIGH_TURNOVER`: Маржа <5% при выручке >5 млрд сум

**Контрагентные (Counterparty):**
7. `SINGLE_BUYER_CONCENTRATION`: >70% выручки на одном покупателе
8. `SINGLE_SUPPLIER_CONCENTRATION`: >60% закупок у одного поставщика
9. `NEW_COUNTERPARTY_LARGE_SHARE`: Новый контрагент >30% оборота за 3 мес
10. `SHELL_COMPANY_PARTNERS`: Контрагенты с ИНН моложе 6 мес
11. `CIRCULAR_INVOICING`: Циклические ЭСФ (deteted via graph analysis)

**Платёжная дисциплина (Payment discipline):**
12. `TAX_PAYMENT_DELAYS`: Задержки уплаты налогов >30 дней
13. `BANK_ACCOUNT_FROZEN_12M`: Приостановка счёта Soliq за последние 12 мес
14. `TAX_PENALTIES_CURRENT_YEAR`: Пеня по налогам в текущем году

**Структурные (Structural):**
15. `DIRECTOR_CHANGED_6M`: Смена директора за последние 6 мес
16. `OKVED_CHANGED_12M`: Изменение основного вида деятельности
17. `LOAN_TO_REVENUE_RATIO`: Запрашиваемая сумма >50% годовой выручки

**Implementation:**
- Каждое правило = pure function `(borrower_data: BorrowerSnapshot) -> RedFlagResult | None`
- Rules registry загружает все правила из YAML при старте
- Run all rules → aggregate severity → produce overall risk score (0-100)
- Logged with rule ID, source, evidence (специфические числа из данных)

**ВАЖНО**: Каждое правило в коде помечено комментарием:
```python
# RULE_SOURCE: ЦБ РУз положение №27-п, п.4.5
# CONFIDENCE: HIGH (regulatory) | MEDIUM (industry practice) | LOW (heuristic)
# VALIDATED_BY: [empty until first bank confirms in pilot]
```

---

## 6. Data Sources & Legal Boundaries

### LEGAL CONSTRAINT (CRITICAL — VIOLATIONS = LAWSUIT)

**Soliq НЕ имеет публичных API для произвольного парсинга чужих данных.** Доступ возможен только:
1. С согласия владельца юрлица (передача через ЭЦП)
2. Через ручную выгрузку самим владельцем (Excel/PDF из my3.soliq.uz)
3. Внутри банковской системы — после получения банком согласия заёмщика на cредитной заявке

**Что МОЖНО парсить:**
- ✅ Excel-выгрузки из my3.soliq.uz, переданные владельцем
- ✅ JSON-выгрузки ЭСФ из api.faktura.uz при наличии токена владельца
- ✅ Открытые реестры юрлиц (gov.uz, stat.uz)
- ✅ Mock-данные для тестов и POC

**Что НЕЛЬЗЯ:**
- ❌ Скрейпить my3.soliq.uz / my.soliq.uz / esf.soliq.uz без авторизации владельца
- ❌ Использовать чужие учётные данные без явного согласия
- ❌ Хранить данные о заёмщиках за пределами периметра банка-клиента

### Data Adapters в коде (priority order)

**v1 (POC + первый пилот):**
1. **`SoliqExcelAdapter`** — парсинг Excel из my3.soliq.uz (выгружает папа/банк/заёмщик)
2. **`EsfJsonAdapter`** — парсинг JSON из api.faktura.uz (когда есть согласие владельца)
3. **`ManualInputAdapter`** — UI-форма ручного ввода (fallback для папы и для случаев без выгрузок)

**v2 (после первого банка):**
4. **`BankAbsAdapter`** — интеграция с АБС конкретного банка (custom для каждого)
5. **`OnlineKkmAdapter`** — данные онлайн-ККМ через банковский интерфейс

**v3 (long-term):**
6. **`SoliqOfficialApiAdapter`** — если/когда Soliq откроет официальный B2B API

---

## 7. Dossier Output (что генерирует продукт)

### HTML+PDF отчёт, structure:

**Раздел A: Идентификация заёмщика**
- ИНН, наименование, ОПФ
- Учредители (с долями)
- Директор (с датой назначения)
- ОКВЭД — основной + дополнительные
- Дата регистрации, юридический адрес
- Размер уставного капитала

**Раздел B: Финансовые показатели (3 года)**
- Выручка по годам (график)
- Чистая прибыль по годам
- Налоговые отчисления
- Активы/обязательства (если есть в отчётности)
- Тренд индикаторы

**Раздел C: Динамика оборотов**
- Helping чарт: помесячная выручка за 24-36 мес
- Сезонность detection
- Outlier annotations

**Раздел D: Контрагенты**
- Топ-10 покупателей (доли в выручке)
- Топ-10 поставщиков (доли в закупках)
- Граф связей (для v2)
- Список новых контрагентов за последние 6 мес
- Подсветка контрагентов-однодневок

**Раздел E: Налоговая дисциплина**
- График задержек уплаты налогов (timeline)
- История блокировок банковских счетов
- Сумма штрафов и пени за 3 года

**Раздел F: Сработавшие красные флаги**
- Список с severity, source, evidence
- Ссылка на правило в config

**Раздел G: Сводная оценка**
- Risk score 0-100
- Recommendation: APPROVE / REVIEW / REJECT
- Confidence level
- Версия rules engine (для аудита)

**Internationalization**: ru-RU + uz-UZ (Cyrillic). Latin uz позже.

---

## 8. Security (BANK-GRADE, NON-NEGOTIABLE)

### Code-level
- Все секреты — только в `.env`, никогда в коде/гите
- `.env.example` в репо, `.env` в `.gitignore`
- Все user inputs — через Pydantic validation
- SQL — только через ORM, никаких raw queries без параметризации
- Passwords — bcrypt (cost ≥12), никогда не plain
- JWT с коротким TTL (15 мин access, 7 дней refresh)
- HTTPS обязателен в любой среде, кроме `localhost:8000`
- CORS strict (только whitelisted origins)
- Rate limiting и account lockout — post-pilot hardening roadmap (см. backlog в CLAUDE.md). На v1 не реализованы — bcrypt cost=12 и MFA остаются единственной защитой brute-force.
- Audit log всех действий с PII (ИНН, имена) — append-only

### Data handling
- Данные заёмщика не покидают периметр банка
- В Bank Mode: storage = БД банка, не наша
- В Accountant Mode: storage = local SQLite на машине бухгалтера, encrypted
- Логи без PII (ИНН маскируется как `XXXXXX1234`)
- Backup стратегия: encrypted, off-site (для production)
- GDPR-style: data deletion API, export API

### Deployment
- Docker images: minimal base (python:3.12-slim), non-root user
- Network: только нужные порты наружу (80, 443, 22)
- Firewall rules: документированы
- Secrets rotation процедура: документирована

### License & IP
- Код — твой IP, не банка
- Договор: банк получает right-to-use, не ownership
- Source escrow для банка (опция): можно обсуждать в pilot

---

## 9. Phased Roadmap

### Phase 0: Foundation (Days 1-3)
- Setup repo (`git init`, GitHub private)
- Setup Python project (`uv` или `poetry`)
- Setup Next.js project в `web/` subfolder
- Docker Compose с PostgreSQL + Redis (для будущего)
- CI: GitHub Actions с линтерами + tests
- README.md + это PROJECT_BRIEF.md
- Базовый CLAUDE.md с conventions
- Hello World endpoint + frontend page (доказательство, что всё подключено)

### Phase 1: Domain Core (Days 4-7)
- Все entities, value objects
- Все 17 rules implemented как pure functions
- YAML rules config + loader
- Unit tests для каждого правила (>90% coverage)
- Synthetic test data (5 фиктивных borrowers с разными профилями)

### Phase 2: Data Adapters (Days 8-12)
- `ManualInputAdapter`: API + UI для ручного ввода всех данных
- `SoliqExcelAdapter`: парсинг 2-3 типовых Excel-форматов
- `EsfJsonAdapter`: парсинг JSON из faktura.uz
- Интеграционные тесты с реальными выгрузками от папы (5 фирм)

### Phase 3: Dossier Generation (Days 13-16)
- HTML template для всех разделов отчёта
- PDF generation через WeasyPrint
- Charts (Recharts) для динамики оборотов и контрагентов
- Russian + Uzbek interfaces

### Phase 4: Bank Mode UI (Days 17-22)
- Bank login screen (mock SSO)
- Borrower search by INN
- Trigger dossier generation
- View results inline + download PDF
- History of analyzed borrowers

### Phase 5: Accountant Mode UI (Days 23-26)
- Local-first variant
- Upload Excel/JSON files
- View dossier как банк увидел бы
- Export для показа клиентам

### Phase 6: Polish & Demo Prep (Days 27-30)
- 60-second demo video recording
- 5 заранее prepared demo scenarios на папиных фирмах
- Onboarding documentation для банка
- Deployment guide для on-premise

**Total: 30 дней до demo-ready MVP при 8h/day.**

---

## 10. Operating Conventions for Claude Code

### Workflow
1. **Перед каждой сессией**: прочитать `PROJECT_BRIEF.md` (этот файл) + `CLAUDE.md`
2. **Plan mode** для каждой нетривиальной задачи (>2 файлов изменений)
3. **Conventional commits**: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
4. **Branch per feature**: `feat/red-flag-engine`, `fix/excel-parser-encoding`
5. **Tests first** для бизнес-логики (TDD для domain layer)
6. **Code review by Claude**: после feature → запросить self-review
7. **No "TODO" without ticket**: каждый TODO имеет ID `# TODO[CA-001]: описание`

### Code style
- Python: ruff defaults + line length 100
- TypeScript: Prettier defaults + strict mode
- Naming: descriptive over short (`get_borrower_dossier_by_inn` > `get_dossier`)
- Comments: WHY, not WHAT
- Type hints везде в Python (`mypy --strict` должен проходить)
- No `any` в TypeScript

### File organization
- One class per file (Python), one component per file (React)
- Tests next to code: `service.py` + `service_test.py`
- Constants в `constants.py`, не магические числа
- DTO отдельно от entities (avoid leaky abstractions)

### Error handling
- Domain errors — typed exceptions (`InsufficientDataError`, `InvalidInnError`)
- Infrastructure errors — wrapped с context
- API errors — structured response с error code + message + details
- Логировать ошибки с full stack trace и request context

### Documentation
- Each module: docstring at top with purpose
- Each public function: docstring with args/returns/raises
- README.md в корне: setup, dev workflow, deployment
- ADRs (Architecture Decision Records) в `docs/adr/`

---

## 11. Anti-patterns (NO MATTER WHAT)

- ❌ Не использовать ChatGPT-стиль buzzwords в UI ("AI-powered", "smart", "intelligent")
- ❌ Не делать многотенантность в POC (один банк = одна установка)
- ❌ Не лезть в ML до Phase 2 (rules engine достаточно для v1)
- ❌ Не использовать SaaS-only зависимости (банк не пустит cloud-only сервисы)
- ❌ Не делать "красивые" анимации в банковском UI (банкиры — серьёзные люди)
- ❌ Не парсить Soliq через scraping (нелегально, см. Section 6)
- ❌ Не хранить данные заёмщиков на dev-машине дольше теста (delete after demo)
- ❌ Не делать публичный GitHub repo (всё в private)
- ❌ Не использовать AI-сгенерённые placeholder тексты (всё на правильном русском)

---

## 12. Definition of Done (для каждой фичи)

Фича считается завершённой, когда:
1. ✅ Код покрыт юнит-тестами (>80% для domain, >60% для остального)
2. ✅ Линтеры проходят без warnings (`ruff`, `mypy --strict`, `tsc --noEmit`)
3. ✅ Документация обновлена (README/ADR/CLAUDE.md если применимо)
4. ✅ Smoke test пройден (фича работает end-to-end через UI)
5. ✅ Code review by Claude (self-review + improvement)
6. ✅ Commit с conventional message
7. ✅ Если изменена API — OpenAPI docs обновлены
8. ✅ Если изменён UI — скриншот в PR description

---

## 13. Working Sessions: How to Use This Brief

При старте новой сессии Claude Code, начни с:

```
@PROJECT_BRIEF.md прочитай этот файл целиком.
Потом @CLAUDE.md.
Потом расскажи мне, на каком phase мы сейчас и какая следующая задача.
```

Когда Claude предлагает решение:
- Спрашивай: соответствует ли архитектуре из Section 4?
- Спрашивай: какие antipatterns из Section 11 могут возникнуть?
- Спрашивай: есть ли source для бизнес-логики (ЦБ-постановление, Базель)?

При большой задаче:
1. План мод сначала
2. Декомпозиция на atomic tasks
3. Implementation по одной atomic task
4. Tests до commit
5. Self-review

---

## 14. References (Sources of Truth)

**Регуляторика:**
- ЦБ РУз: cbu.uz (постановления о кредитной политике, Базель III адаптация)
- Soliq.uz: налоговое законодательство, формы отчётности
- НК РУз (Налоговый кодекс): актуальная редакция

**Технические:**
- my3.soliq.uz: личный кабинет налогоплательщика (для понимания структуры данных)
- api.faktura.uz/help: документация API ЭСФ
- gov.uz: открытые реестры юрлиц

**Banking industry:**
- KPMG Uzbekistan banking report 2025
- CERR (Центр экономических исследований и реформ): квартальные обзоры банков
- Group-IB: отчёты по фроду в UZ

**Tech stack:**
- FastAPI: fastapi.tiangolo.com
- SQLAlchemy 2.0: docs.sqlalchemy.org
- Next.js 15: nextjs.org
- shadcn/ui: ui.shadcn.com
- Pydantic v2: docs.pydantic.dev

---

## 15. Final Note for Claude Code

Это **production-grade проект для банковского сектора**, не пет-проджект. Каждая строчка кода может стать предметом аудита. Безопасность > скорости. Качество > фичей. Правильная архитектура > "работает".

Если есть сомнения — **спроси**. Не предполагай.
Если есть anti-pattern — **остановись**. Не продолжай.
Если меняется domain logic — **подтверди источник**. ЦБ-постановление или гипотеза.

Founder работает один, через AI-orchestration. Это значит:
- Код должен быть **самообъясняющимся** (founder вернётся к нему через 3 месяца)
- Тесты — это **документация поведения**
- Коммиты — это **journal проекта**
- Архитектура — это **защита от хаоса** при росте

Ship it like senior, not like vibe-coder.
