# Pre-Demo Roadmap

> Owner: Riobvo · Updated: 2026-05-18 · Status: active
> Источник истины по приоритизации до bank demo. CLAUDE.md содержит только compact-summary.

**Critical rule:** работаю ТОЛЬКО над активным Tier. Всё что не в Tier 0–4 — Frozen.

**Tier 0 status (2026-05-18):** ✅ **closed**. T0.1 / T0.2 / T0.3 / T0.4 / T0.5 done. T0.4 follow-up (B1+B2+B3+B4 + CA-DS29-apostrophe) тоже closed.

**Tier 1 / T1.1 (2026-05-18):** ✅ **closed**. Compromised B исполнен — sequence на `dossiers.case_id`, миграция `b3e9f1a7d4c5` + `CaseIdAllocator` + drop derived helpers. Existing 47 dossiers backfilled `BR-2026-0001..0047`.

**Tier 1 / T1.2 (2026-05-18):** ✅ **closed**. ADR-0016. `RefreshTokenDenylistPort` + `RedisRefreshTokenDenylist` (`SET NX EX` + TTL clamp) + `NullRefreshTokenDenylist` fallback. `/refresh` rotation, `/logout` денилист'ит refresh из BFF cookie. **Active — T1.3 PII encryption at rest (column-level через app-layer, не наивный pgcrypto на JSONB).**

---

## Open decisions (quick scan)

Подвешено — закроется при старте соответствующего Tier. Если забываешь — этот блок ловит первым при чтении roadmap.

- ~~**T0.4 / pre-impl check**~~ ✅ **resolved 2026-05-17**: `dossier_mapper.py:15-28` сериализует только `rule_id` + `rule_version`, `rule.name` в JSONB не уходит. Backlog: per-version registry loader для historical-name immutability (использовать существующий `rule_version`) — не сейчас.
- ~~**T0.4 / pick-on-start**~~ ✅ **resolved 2026-05-18**: ADR-0015 зафиксировал гибрид (b) template-level JSON dict + (c) branchless для `rule.name`. T0.4 закрыт.
- ~~**T1.1 / target-table**~~ ✅ **resolved 2026-05-18**: compromised B — sequence на `dossiers` table, не на Phase 4 application entity (full Phase 4 = 5-10 дней refactor, ставит demo timeline под риск). Dossier = de-facto application proxy в текущей arch; post-demo case_id переносится на applications через FK без потерь.
- ~~**T1.1 / wizard preview**~~ ✅ **resolved 2026-05-18**: (c) wizard показывает placeholder «case_id будет назначен» pre-submit. Реальный SEQ выдаётся при successful dossier creation. Drop `formatCaseId(draft.draftId)` derived формат и его frontend helper (`web/src/features/manual-input/lib/case-id.ts` + test).
- ~~**T1.1 / race-safety**~~ ✅ **resolved 2026-05-18**: advisory lock `pg_advisory_xact_lock(year_hash)` на year-boundary reset. Avoids `LOCK TABLE` overhead.

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



### T0.1 — Real soliq fixtures via personal ETSP ✅ DONE 2026-05-18
- ✅ 4 фирмы × 5 типов = formal набор complete. ИНН: 201308534, 305002665, 308747266, **305738460** (последняя добавлена 2026-05-18, sparse ilova как у фирм 1 и 3).
- ✅ Файлы лежат в `tests/fixtures/soliq_xltx/` (gitignore по pattern `*_full.xltx`). По факту 28 xltx с учётом q4 / monthly variations.
- ✅ Acceptance: `tests/parsers/real_xltx_test.py` 19/19 pass + 4 xfail (T2.3 profit_tax pending).
- ⏳ **CA-DS30** anonymize gap: только 1/28 `*_anon.xltx` на месте. Bulk anonymization через openpyxl script (per-format replace правил для ИНН/имён/сумм с сохранением signature-cells) — post-T1 priority в backlog.

### T0.2 — CBU API real integration (CA-024b) ✅ DONE 2026-05-17 (commit b124af6)
- ✅ Adapter `infrastructure/external/cbu_client.py` поверх `cbu.uz/oz/arkhiv-kursov-valyut/json/USD/`.
- ✅ Per-call `async with httpx.AsyncClient`, timeout 3s + 2 retries (0.5s/1s backoff), `CBU_API_URL` env override, User-Agent identity.
- ✅ Postgres caching: table `usd_uzs_rates(date PK, rate Decimal(14,4), nominal, source, fetched_at, raw_response jsonb)` с idx date DESC. ON CONFLICT (date) DO NOTHING.
- ✅ Service `application/services/usd_rate_service.py` — fallback chain env → DB today → CBU live (save) → DB latest → JSON bootstrap → ExchangeRateError.
- ✅ Endpoint `/api/system/usd-rate` через DI service, source enum: `env | cbu_live | db_cached | manual | fallback`.
- ✅ ADR-0014 «External API integration pattern (CBU as reference)» — шаблон для T0.3 ГНК Phase A, T2.4 faktura.uz, CA-DS28 ГНК public.
- ✅ Tests: 6 unit CBU client (mock httpx.MockTransport) + 7 unit service (6 веток fallback) + 5 integration repository (testcontainers) + 5 integration endpoint (mock fetch). Live smoke на cbu.uz: rate=11975.36, asof=2026-05-15.
- ⏳ Legal review CBU public data — параллельно (запросы юриста, не блокер).
- ⏳ Daily background fetch / 90-day retention автоудаление — отложено в T3 (operational readiness).

### T0.3 — ГНК Phase A: manual upload (CA-003 Phase A) ✅ DONE 2026-05-18
- ✅ **Backend** (`53ac8fe`): GnkCertificate value object + Alembic migration `a1f3c5e8b9d2` (gnk_certificates + BYTEA file storage) + Repository + Service (upload + fetch заглушка для Phase B) + 3 endpoints (POST upload / GET latest / GET file download) + snapshot_mapper round-trip + tests. ADR-0014 pattern.
- ✅ **T0.3.1** (`feabb3a`) — frontend wizard Step 1 upload UI: `GnkCertificateUpload` component с innValid gate + GET existing + multipart POST + client validation (size/mime). i18n ru+uz. 4 RTL.
- ✅ **T0.3.2** (`9cb20a6`) — display в досье + PDF: DossierViewResponse.gnk_certificate optional, BorrowerCard pill (active/suspended/revoked/unknown × uploaded/live/cached/fallback), Section A PDF row. i18n ru+uz. 3 RTL + template test.
- ⏳ Phase B (CA-DS28 public lookup на soliq.uz/services/search/) — после legal-clearance.

Live-browser smoke не выполнен в этой сессии (требует Docker + manual walkthrough). Lesson `feedback_nested_anchor_rtl_blind`: перед мержем в prod-ветке пройти full upload → display flow.

### T0.4 — UZ-локализация PDF (CA-DS29-pdf) ✅ DONE 2026-05-18

8 коммитов от `ce2c47a` (ADR-0015) до `a7de8a3` (endpoint `?lang=`):

1. `ce2c47a` — **ADR-0015**: гибридный подход (b)+(c) — template-level JSON dict для chrome + branchless conditional для `rule.name`. Альтернативы gettext / pure branchless отвергнуты.
2. `0a3a1d6` — **Domain + schema**: `Rule.name_uz` поле, `RuleSpecYaml.name_uz` required (`min_length=1`), registry_factory пробрасывает, placeholder-миграция YAML.
3. `54c9574` — **YAML финальные переводы**: 19 правил UZ через Soliq-стандартную терминологию (QQS, EHF, soʻm). ОКВЭД остался кириллицей, INN латиницей — banking convention.
4. `95187c4` — **i18n infra**: `config/pdf-i18n/{ru,uz}.json` (~111 ключей с dotted-namespaces + month arrays), `PdfMessages` DTO, loader с `lru_cache(maxsize=2)`, 12 unit-тестов (happy ru/uz, subkey symmetry, format placeholders, negative paths, cache identity).
5. `7b74129` — **Use-case wiring**: `RenderDossierPdf.execute(dossier_id, lang)`, `DossierPdfBundle.lang/.messages`, DI injection `pdf_messages_loader`, per-lang `rule_names` через `_rule_name_for_lang`.
6. `2f7f753` — **observations_builder rewrite**: f-strings → `messages.X.format(pct=..., years=..., chain=..., year=..., prior_year=..., ratio=...)`. +4 UZ-теста на head/num/ctx локализацию.
7. `4707956` — **Templates + Python labels**: `dossier.html` все RU-literals → `{{ t.X }}`, page footer CSS counter sandwich, `template_filters.py` closure-factories, `chart_renderer.py` принимает messages, `pdf_renderer.py` контекст с `t = messages`, removed module-level RU mappings (recommendation/legal_form/kpi_label/signal_breakdown/evidence_label).
8. `a7de8a3` — **Endpoint `?lang=`**: `Query(default=None, "ru"|"uz")`, fallback chain `query → brand.default_lang → "ru"`, `BrandConfig.default_lang` optional поле, audit-log `payload={"lang": ...}`.

**Hygiene fix внутри commit 7**: methodology «17 правил» → `{rules_count}` placeholder, резолвится из `dossier.rules_evaluated` (sync с фактическими 19 в YAML).

**Acceptance**: `GET /api/dossier/{id}/pdf?lang=uz` рендерит полностью узбекское досье без RU-fallback в content. Tested на 793/793 local pytest + ruff + mypy strict + CI зелёный. Live-browser/WeasyPrint smoke (нужен Docker `api`) пока не выполнен в Windows-сессии — heads-up для production-merge.

**Backlog (не T0.4)**: per-version registry loader для historical-name immutability (`rule_version` уже сериализуется, можно подгружать old YAML); `uzbekbank.json` получит `"defaultLang": "uz"` после UZ-demo validation.

---

## Tier 1 — Prod-killers (после T0)

### T1.1 — case_id monotonic sequence (CA-DS18b/c) ✅ DONE 2026-05-18

Compromised B: sequence на `dossiers.case_id` (не Phase 4 application entity).

- ✅ Alembic migration `b3e9f1a7d4c5`: `CREATE SEQUENCE dossier_case_seq` + `ADD COLUMN case_id VARCHAR(20) UNIQUE NOT NULL` + backfill `ROW_NUMBER() OVER (PARTITION BY EXTRACT(YEAR FROM created_at) ORDER BY created_at, id)` + setval на MAX+1 для current year. 47 existing dossiers backfilled `BR-2026-0001..0047`.
- ✅ `CaseIdAllocatorPort` + `SqlAlchemyCaseIdAllocator`: `pg_advisory_xact_lock(year)` → проверка `MAX(SUBSTRING(case_id FROM 4 FOR 4)::int)` → year shift trigger'ит `ALTER SEQUENCE dossier_case_seq RESTART WITH 1` → `nextval`. Lesson из TDD: на пустую БД (max=NULL) **не reset'им** — sequence уже sync'ed миграцией.
- ✅ `DossierViewRecord +case_id`, `dossier_repo.save(record, snapshot_id, case_id, ...)` обязательный позиционный.
- ✅ Drop derived helpers: `_application_id` в `dossier_mapper.py` + `_format_application_id` в `pdf_renderer.py`. Оба читают `view.case_id`.
- ✅ Frontend: удалены `web/src/features/manual-input/lib/case-id.ts` + test, `manual-input-view.tsx` рендерит `caseId={null}` (PageHead показывает «—»).
- ✅ Tests: 7 unit (allocator) + 4 integration testcontainers (allocator) + 8 update'ов на новую save() сигнатуру (snapshot_dossier / dossier_view / dossier_source_mode / bank_search / bank_stats / bank_history / dossier_get / dossier_test / draft_test) + 4 update'а DossierViewRecord constructor (load_dossier_for_view_test / load_dossier_readiness_test / render_dossier_pdf_test / pdf_renderer_test).
- ✅ E2E smoke: `POST /api/manual-input` → `case_id=BR-2026-0048` (после 47 backfilled).
- ✅ Closes CA-DS18b (banking sequence) + CA-DS18c (year edge).

**Scope reality:** ~22 файла (план оценивал ~10 — underestimate). Lesson: pre-impl grep `DossierViewRecord(...)` callers поймал бы +4 callsite раньше.

**Pre-existing issue замечен (вне T1.1 scope):** `tests/infrastructure/rules/test_registry_factory.py::test_yaml_with_unknown_rule_raises` падает на T0.4 B1 regression (`source_uz` required в `RuleSpecYaml`, inline YAML в тесте не обновлён). Подтверждено `git stash` → fail. Отдельный hotfix.

### T1.2 — Refresh-token rotation + Redis denylist (CA-019) ✅ DONE 2026-05-18

ADR-0016 «Refresh-token rotation». Compromise design:
- ✅ `RefreshTokenDenylistPort` (Protocol) + `RedisRefreshTokenDenylist` (atomic `SET NX EX`, TTL clamp до 1s) + `NullRefreshTokenDenylist` (no-op, активируется при `REDIS_URL=None`).
- ✅ `/api/bank/auth/refresh`: decode → `is_denied(jti)` → `is_active` → `deny(jti)` NX → выдаёт новые access + refresh. NX=False → 401 `token_reused`.
- ✅ `/api/bank/auth/logout`: optional `LogoutRequest.refresh_token` body. Backend decode + cross-account guard (`claims.analyst_id == analyst.id`) + denylist. Best-effort: невалидный/чужой токен silently skip.
- ✅ Frontend BFF: refresh route обновляет **обе** cookies из upstream response; logout прокидывает `refresh_token` из cookie в backend body.
- ✅ Settings: `redis_url: str | None = None`. Compose `REDIS_URL=${REDIS_URL:-redis://redis:6379/0}` + `depends_on: redis healthy`.
- ✅ Fallback policy: `REDIS_URL=None` → NullDenylist (stateless 7д режим сохраняется для dev). `REDIS_URL` задан, Redis недоступен → fail closed (ConnectionError всплывает → 500), compromised tokens не проскочат.
- ✅ Tests: 2 unit (Null) + 6 unit (Redis fakeredis: deny/race/is_denied/TTL/clamp) + 2 integration (testcontainers redis: deny+is_denied, NX-winner) + 24 integration на bank_auth_test (4 новых rotation/double-use/chain/cross-account-logout + 3 расширения).
- ⏳ Redis HA / sentinel — deferred в T3 (operational readiness).

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
- **CA-DS30** — anonymize gap для real xltx fixtures. Сейчас 1/28 `*_anon.xltx` на месте. Bulk anonymization через openpyxl script: per-format (VAT_DECLARATION / VAT_REGISTRY_ILOVA / FORM_2 / FORM_1 / PROFIT_TAX) replace правил для ИНН (на dummy ИНН) / имён (синтетика) / сумм (random preserving order-of-magnitude + signature-cells для parser format-detection). Скрипт `scripts/anonymize_xltx.py` + 28 anonymized output → git. **Post-T1 priority** (после T1.1-T1.5 prod-killers).
