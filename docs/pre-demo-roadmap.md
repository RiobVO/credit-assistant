# Pre-Demo Roadmap

> Owner: Riobvo · Updated: 2026-05-17 · Status: active
> Источник истины по приоритизации до bank demo. CLAUDE.md содержит только compact-summary.

**Critical rule:** работаю ТОЛЬКО над активным Tier. Всё что не в Tier 0–4 — Frozen.

---

## Open decisions (quick scan)

Подвешено — закроется при старте соответствующего Tier. Если забываешь — этот блок ловит первым при чтении roadmap.

- ~~**T0.4 / pre-impl check**~~ ✅ **resolved 2026-05-17**: `dossier_mapper.py:15-28` сериализует только `rule_id` + `rule_version`, `rule.name` в JSONB не уходит. T0.4 unblocked. Backlog: per-version registry loader для historical-name immutability (использовать существующий `rule_version`) — не сейчас.
- **T0.4 / pick-on-start** — стиль локализации Jinja2 strings: `gettext` vs in-template dict vs branchless `{{ rule.name_ru if lang == 'ru' else rule.name_uz }}`. Не блокер, но при старте T0.4 зафиксировать ОДИН подход — иначе 3 стиля в одном feature.

---

## Resolved decisions (зафиксировано, чтобы не пересматривать)

- **T1.1 year rollover** → application-level reset (не Postgres trigger). Гибче для on-prem (явный код в use-case, легче дебажить через логи, переносится между инстансами без db-script).

---

## Definition of "ready for bank demo"

1. Реальные данные сквозь весь pipeline (не fixtures, не JSON, не hardcode).
2. UZ-локализация UI + PDF до уровня compliance officer.
3. Compliance baseline: PII encryption, audit-log retention, refresh-token rotation, SSO-ready.
4. Prod-deploy procedure воспроизводима (Ansible / Docker compose + systemd).
5. 15 реальных xltx (5 типов × 3 компании) прогнаны end-to-end без unexpected warnings.

---

## Frozen scope (не трогать до post-demo)

- UI polish: новые цвета, шрифты, тени, анимации.
- Расширения dark theme, 4-я тема, accent variants.
- Новые design tokens, brand-tenant новые секции (текущих support/businessHours достаточно).
- CA-DS25 (KPI sparkline), новые OKVED-каталог расширения сверх текущего baseline.
- i18n keys refactor, новые ADR по визуальному дизайну.
- Coverage сверх текущего baseline ради числа — кроме тестов на новый код Pre-Demo.
- Refactor без бизнес-причины из этого roadmap.

---

## Tier 0 — Deal-breakers (active)

### T0.5 — VAT parser fix for real 10006_41/45/47 formats ✅ DONE 2026-05-17 (commit f5d7495)
Промоут из Tier 2 (CA-015) — раскрыто прогоном `tests/parsers/real_xltx_test.py`
на real-фикстурах от 3 фирм. Парсер падал на:
- **NKM ilova** — розничные продажи через онлайн-кассу с пустым counterparty name.
- **Trailing empty rows** — Soliq оставляет зарезервированные rows в конце листа.
- **vat_decl legacy 10006_41** — header layout сдвинут влево на 2-4 колонки (декабрь 2025).

Detection — structural через `list01.max_column` (v1=13, v2=19, threshold=14),
не sentinel-substring. Body (list02/list04) идентичен — отличается только шапка.

Acceptance: 19 real-xltx pass (form1/form2 ×3 фирмы, vat_decl ×4, vat_ilova ×4 +
существующие), 4 xfail (profit_tax — T2.3 pending). 0 failed.



### T0.1 — Real soliq fixtures via personal ETSP
- **Цель**: 3–4 собственные фирмы × 5 типов xltx = 15–20 реальных файлов. Выгрузка через личные кабинеты soliq.uz по моим ЭЦП.
- **Куда**: `tests/fixtures/real/` (gitignore). Анонимизированные версии (замазанные ИНН/имена/суммы) в `tests/fixtures/real_anon/*.xltx` — в git.
- **Acceptance**: `tests/integration/test_real_xltx.py` прогон через все 5 парсеров → 0 unexpected `parse_warnings` (whitelist допустимых документирован в тесте).

### T0.2 — CBU API real integration (CA-024b)
- Adapter `infrastructure/external/cbu_client.py` поверх `cbu.uz/oz/arkhiv-kursov-valyut/json/`.
- Daily Postgres caching, fallback на last-known rate, 90-дневная история для аудита.
- Legal review запустить параллельно (mirror CA-DS28: уз-юрист 30 мин + robots.txt check).
- **Acceptance**: `GET /api/system/usd-rate` отдаёт live rate + `as_of` timestamp + `source: "cbu_live" | "cached" | "fallback"`.

### T0.3 — ГНК Phase A: manual upload (CA-003 Phase A)
- Аналитик грузит PDF/JPG справки + ручной ввод полей (имя, ИНН, статус, ОКВЭДы).
- Domain: `BorrowerSnapshot.gnk_certificate: GnkCertificate | None` с `source: "uploaded"`, `uploaded_at`, `uploaded_by_analyst_id`.
- Phase B (public lookup) — после legal-clearance (CA-DS28), не сейчас.
- **Acceptance**: end-to-end — аналитик загружает справку → данные попадают в snapshot → отображаются в досье + PDF.

### T0.4 — UZ-локализация PDF (CA-DS29-pdf)
Декомпозиция (не однострочник):

1. **Templates**: перевести все Jinja2 templates на UZ (заголовки секций A–F, KPI tile labels, severity-labels, observations headers).
2. **Domain schema**: `Rule.name_uz: str` поле в `domain/rules/rule.py`.
3. **YAML migration**: `config/rules/v*.yaml` — добавить `name_uz` для каждого rule (~30 правил, manual translation).
4. **Registry factory**: `domain/rules/registry_factory.py` пробрасывает `name_uz` через `RuleRegistry`.
5. **Snapshot mapper** ✅ **verified 2026-05-17**: `dossier_mapper.py:15-28` сериализует только `rule_id` + `rule_version`. `rule.name` / `name_uz` в JSONB не уходят — round-trip существующих snapshots не ломается. Backlog (не T0.4): per-version registry loader для historical-name immutability — `rule_version` уже сериализуется, можно подгружать old YAML.
6. **Endpoint**: `dossier_pdf.py` принимает `lang: Locale` query, `RenderDossierPdf.execute(dossier_id, lang)` передаёт в Jinja2 context.
7. **Localization style** ⚠ **pick-on-start (open)**: один из трёх — Python-side `gettext` / template-level dict / branchless `{{ rule.name_ru if lang == 'ru' else rule.name_uz }}`. Зафиксировать ОДИН до первого PR — иначе 3 стиля разъедутся по templates.

**Acceptance**: `GET /api/dossier/{id}/pdf?lang=uz` рендерит полностью узбекское досье без RU-fallback в content (brand-strings типа имени банка остаются как в config).

---

## Tier 1 — Prod-killers (после T0)

### T1.1 — case_id monotonic sequence (CA-DS18b)
- Postgres sequence `application_case_seq` в `applications` table.
- Формат `BR-{YYYY}-{seq:04d}`. **Year rollover → application-level reset** (resolved): use-case проверяет `current_year != last_issued_year` и ресетит sequence через `ALTER SEQUENCE ... RESTART`. Trigger в БД отвергнут — application-level гибче для on-prem, явный код, читаемые логи.
- Frontend `formatCaseId` переключается на чтение `application.case_id` с бэка.
- Замыкает одновременно CA-DS18c (year edge case).

### T1.2 — Refresh-token rotation + Redis denylist (CA-019)
- Redis сервис в `docker-compose.yml`.
- Rotate refresh-token на каждый `/api/auth/refresh`.
- Denylist старых tokens до их expiry (TTL = refresh-token lifetime).
- Совместимость: existing stateless 7д режим остаётся как fallback при отсутствии Redis в dev.

### T1.3 — PII encryption at rest (column-level через app-layer)
**Не наивный pgcrypto на JSONB** — это сломает queryability и индексирование.

Декомпозиция:
1. **Inventory**: какие колонки реально содержат PII.
   - `borrowers.inn` (ИНН — PII).
   - `analysts.full_name` (имя — PII).
   - `audit_log.payload` (содержит PII в JSON).
   - `dossiers.snapshot_json.financial_report` (финансы — конфиденциально, не PII в строгом смысле).
   - `dossiers.snapshot_json.gnk_certificate` (PII).
2. **Decision per column**:
   - Plain `text` PII колонки (ИНН, имя) → application-layer encrypt через `cryptography.Fernet` (symmetric AES-128 GCM), хранить как `text` base64.
   - JSONB колонки с mixed-data → **не encrypt целиком**. Вместо этого: encrypt sensitive sub-fields на уровне serializer (`_financial_report_to_dict` шифрует `taxpayer_name` если есть). Query-able поля остаются plain.
3. **Master key**: env `PII_ENC_KEY` (32 байта base64) или Vault. Procedure rotation в `docs/operations/pii-key-rotation.md`.
4. **Migration**: data-migration encrypts existing rows одной транзакцией (small dataset, тысячи строк, не миллионы).
5. **ADR**: написать ADR-0014 "PII encryption strategy" до начала.

**Acceptance**: `SELECT inn FROM borrowers LIMIT 1` отдаёт base64 ciphertext, через application-слой расшифровывается прозрачно. Key rotation procedure пройдена в dry-run.

### T1.4 — Multi-tenant isolation (runtime, не build-time)
**Не build-arg per brand image** — N образов + CI matrix + registry storage избыточно. Build-arg не даёт значимой security gain (image тоже reverse-engineer'ится).

Текущий подход: `BRAND_ID` runtime env. Усилить:
1. **Startup assertion**: при старте API сравнить `os.environ["BRAND_ID"]` с `config/brands/<id>.json` — если файла нет или brand_id mismatch, crash на boot, не отдавать requests.
2. **Cross-tenant guard**: все queries через `borrowers` фильтруются по `brand_id` колонке (добавить если нет) — single SQL view `borrowers_for_current_brand` или middleware filter.
3. **Audit trail**: `audit_log.brand_id` колонка, indexed.
4. **Deploy doc**: `docs/operations/multi-tenant-deploy.md` — одна команда `BRAND_ID=uzbekbank docker compose up` на инстанс банка.

**Acceptance**: разворачиваешь 2 инстанса на одной машине (`uzbekbank` + `demo`), запросы между ними изолированы на DB-level.

### T1.5 — LDAP/OAuth AuthnAdapter (CA-020)
- `LdapAuthnAdapter` поверх существующего `AuthnPort`.
- Group → role mapping из LDAP attributes.
- Local fallback для break-glass admin (env `ADMIN_BREAK_GLASS_EMAIL`).
- Конфигурация per-deployment через env (LDAP URI, base DN, bind credentials).

---

## Tier 2 — Data quality (после T1)

- **T2.1** — Dynamic unit detection FORM_2 (CA-028). Header parsing «в тысячах/миллионах сум», сейчас hardcoded ×1000.
- ~~**T2.2** — VAT parser на реальных 10006_45/10006_47 (CA-015)~~ → **поглощено T0.5 done 2026-05-17 (commit f5d7495)**.
- **T2.3** — PROFIT_TAX parser (CA-029b). 15 листов, сейчас adapter raises `UnsupportedFormatError`. Замыкает CA-DS25 (KPI sparkline) как side-effect.
- **T2.4** — faktura.uz integration (CA-DS11). Сейчас в `/api/system/health` всегда `not_implemented`.

---

## Tier 3 — Operational readiness (после T2)

- **T3.1** — Observability: Sentry или GlitchTip on-prem (CA-064). Backend + frontend `error.tsx` hook.
- **T3.2** — Structured logging с `correlation_id` сквозь все слои (request → use-case → adapter). `logging.Filter` injection через FastAPI middleware.
- **T3.3** — Prometheus `/metrics` + Grafana dashboard pack (latency p50/p99, error rate, PDF gen time, parser warnings rate).
- **T3.4** — Postgres backup: `pg_dump` daily + retention 30d + restore drill, документ в `docs/operations/db-backup.md`.
- **T3.5** — Audit log export: `GET /api/admin/audit-log/export?from=...&to=...` → CSV.
- **T3.6** — On-prem deploy: Ansible playbook или Docker compose + systemd unit + README «0 → running» за <30 минут.

---

## Tier 4 — Compliance pack (параллельно с T1–T3, начать за 2 мес до подачи)

- **T4.1** — Penetration test от лицензированной узб-лаборатории (есть несколько вендоров — выбрать после консультации с банковским procurement). Отчёт нужен для tender package.
- **T4.2** — Аттестат соответствия УзСтандарта на обработку ПДн (Закон РУз «О персональных данных» №547). Процесс 2–3 месяца, нужны documented procedures.
- **T4.3** — Резидентство в IT-юрисдикции РУз (IT Park / Uzinfocom) — закупочное требование госбанков.
- **T4.4** — Документация: Admin Guide · Security Architecture · DRP/BCP. Каждый документ — RU + UZ, PDF, версионирование в git.

---

## Заблокированные (pre-condition не выполнен)

- **CA-DS18c** formatCaseId year edge — pre-condition: T1.1 + `useFormDraft` пробрасывает `draft.created_at`. Замыкается одновременно с T1.1.
- **CA-DS25** KPI sparkline — pre-condition: T2.3 PROFIT_TAX parser. Frozen до пост-демо.
- **CA-DS28** ГНК public lookup (CA-003 Phase B) — pre-condition: legal review закрыт.
- **CA-029b full scope** — это и есть T2.3.

---

## Backlog (вне Roadmap, могут не понадобиться)

- **CA-015b** — VAT-парсер для следующих xltx-форматов сверх T0.1 пакета. Оценить после T0.1.
- **CA-DS11b** — faktura.uz расширенный scope (queries, history). Оценить после T2.4.
