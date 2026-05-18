# Pre-Demo Roadmap

> Owner: Riobvo · Updated: 2026-05-18 · Status: active
> Источник истины по приоритизации до bank demo. CLAUDE.md содержит только compact-summary.

**Critical rule:** работаю ТОЛЬКО над активным Tier. Всё что не в Tier 0–4 — Frozen.

**Tier 0 status (2026-05-18):** ✅ **closed**. T0.1 / T0.2 / T0.3 / T0.4 / T0.5 done. T0.4 follow-up (B1+B2+B3+B4 + CA-DS29-apostrophe) тоже closed.

**Tier 2 status (2026-05-18):** ✅ **closed**. T2.1 / T2.2 / T2.3 / T2.4 done. Переход к **Tier 3 (Operational readiness)**.

**Tier 1 / T1.1 (2026-05-18):** ✅ **closed**. Compromised B исполнен — sequence на `dossiers.case_id`, миграция `b3e9f1a7d4c5` + `CaseIdAllocator` + drop derived helpers. Existing 47 dossiers backfilled `BR-2026-0001..0047`.

**Tier 1 / T1.2 (2026-05-18):** ✅ **closed**. ADR-0016. `RefreshTokenDenylistPort` + `RedisRefreshTokenDenylist` (`SET NX EX` + TTL clamp) + `NullRefreshTokenDenylist` fallback. `/refresh` rotation, `/logout` денилист'ит refresh из BFF cookie.

**Tier 1 / T1.3 (2026-05-18):** ✅ **closed**. ADR-0017. `PiiEncryptorPort` + `FernetPiiEncryptor` (`MultiFernet` rotation) + `NullPiiEncryptor` fallback. SQLAlchemy TypeDecorator (`EncryptedString`/`EncryptedJsonb`/`EncryptedBytea`) на 6 PII колонках. `audit_log` emails masked. Alembic `c5d2f3a7e1b4` (length expansions + data encrypt pass, idempotent). Production startup-assertion. Runbook `docs/operations/pii-key-rotation.md`.

**Tier 1 / T1.4 (2026-05-18):** ✅ **closed**. ADR-0018. Approach A pure — single-tenant per deployment (separate compose-project per bank), scope сужен после PROJECT_BRIEF Sec 11 review. `Settings.brand_id` + `_validate_runtime_config` helper в `app.py` (BRAND_ID resolves + PII_ENC_KEYS prod-mandatory, обобщает T1.3 inline check). `load_brand(brand_id)` mandatory arg — env-fallback внутри loader убран. `audit_log.brand_id` колонка (Alembic `e7f9a3c2b8d1`, NOT NULL DEFAULT 'default' + index `(brand_id, created_at)`) для forensics. Repository конструктор принимает brand_id, 5 callsites пробрасывают `settings.brand_id`. Playbook `docs/operations/multi-tenant-deploy.md`.

**Tier 1 / T1.5 (2026-05-18):** ✅ **closed**. ADR-0019. LDAP-only, scope сужен — OAuth defer'ится в T1.5b backlog. `AUTHN_MODE=seeded|ldap` env switch (default `seeded`). LDAP integration через `ldap3` (pure Python, no system deps). `LdapAuthnAdapter` (service-bind → search → user-bind verify, role resolution через memberOf, lazy upsert) + `Ldap3Client` wrapper + `BreakGlassAuthnAdapter` (email whitelist → seeded fallback, source override на `break_glass`). `AuthnPort.authenticate` теперь возвращает `AuthnResult(identity, source)` — audit-log payload содержит `authn_source` для compliance trail. Alembic `f4a2d6c9e3b8`: `analysts.password_hash` NULLABLE + `authn_source VARCHAR(20) NOT NULL DEFAULT 'seeded'` + CHECK constraint. `_validate_runtime_config` ловит missing LDAP_* env при `AUTHN_MODE=ldap`. Playbook `docs/operations/ldap-setup.md` (generic AD defaults + ops runbook). **Tier 1 complete — переход к Tier 2 (Data quality).**

**Tier 2 / T2.4 (2026-05-18):** ✅ **closed** as honest stub. ADR-0020 «Defer faktura.uz real integration until bank-provided token». Real client integration ждёт пилот-банка с OAuth-токеном — без него mock-only client с придуманным форматом JSON даёт fake-green confidence. Текущий ESF path — Excel-выгрузка my3.soliq.uz (VAT_REGISTRY_ILOVA), работает на real-data. Backend tip /api/system/health и frontend badge «В разработке» → «Опционально» (RU) / «Ixtiyoriy» (UZ). Status enum `not_implemented` оставлен в API contract — переименование invasive без user-facing payoff. Closes CA-DS11 (messaging gap). Real-client integration → T2.4b backlog.

**Tier 2 / T2.1 (2026-05-18):** ✅ **closed**. Dynamic unit detection FORM_2 + FORM_1 (scope расширен по сравнению с roadmap первоначальным — FORM_1 имел тот же hardcoded `_THOUSANDS_MULTIPLIER` gap). 4 атомарных коммитов: T2.1.1 `parse_unit_multiplier(wb, fmt) -> (Decimal, str | None)` helper в `header_parser.py` (case-insensitive substring matching: «млн» → ×1_000_000, «тыс» → ×1_000, «сум»/«soʻm» → ×1, unknown/empty → fallback ×1_000 + warning); T2.1.2 form2_parser wiring (16 money-cells × 2 helpers); T2.1.3 form1_parser wiring (22 балансовых cells + _aggregate_debt 5 компонент); T2.1.4 docs sync. Backward compat: 13/13 real fixtures = «тыс. сум.» → ×1000, поведение не меняется. Real-fixture smoke на «млн / полные сум» branches — backlog (T2.1b, нет fixture от папы). Tests: 10 unit helper + 5 FORM_2 + 5 FORM_1. 336/336 pytest pass (28 real fixtures), ruff + mypy strict clean. Closes CA-028.

**Tier 2 / T2.3 (2026-05-18):** ✅ **closed**. PROFIT_TAX parser (5-й и последний xltx-формат my3.soliq.uz) подключён end-to-end в 5 атомарных коммитах (T2.3.1-5). `ProfitTaxData` DTO (минимум: header + taxable_profit + profit_tax_total), `parse_profit_tax(wb)` читает list01 L31 (код 030 Налогооблагаемая прибыль, signed) + L39 (код 080 Сумма налога — gross computed). Multiplier ×1 (полные сум, не тыс. как FORM_2) — cross-check L29 ≈ FORM_2 F6 × 1000. `SoliqXltxAdapter._dispatch` диспетчит PROFIT_TAX, `ParseManualInputFilesUseCase._merge_profit_tax` пишет в `taxes_paid_by_year[year]` через `_set_once`. Quarterly (Q1/Q2/Q3) — silent skip с warning (mirror FORM_2 CA-027 option b, защита от Q1 layout drift в L36). Tests: 8 unit parser + 6 unit use-case + 5 PROFIT_TAX fixtures pass в `real_xltx_test.py` (раньше xfail). 316/316 pytest (application + adapters + parsers), ruff + mypy strict clean. Closes CA-029b. **Heads-up CA-DS25 correction:** roadmap утверждал что T2.3 «замыкает CA-DS25 (KPI sparkline)» — это **ошибка**: sparkline требует monthly_turnover≥12 источник (VAT_DECL chain или ESF), не annual PROFIT_TAX. CA-DS25 остаётся frozen с обновлённым pre-condition.

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

### T1.3 — PII encryption at rest (column-level через app-layer) ✅ DONE 2026-05-18

ADR-0017 «PII encryption at rest». Design:
- ✅ `PiiEncryptorPort` (Protocol) + `FernetPiiEncryptor` (`MultiFernet` для rotation) + `NullPiiEncryptor` (passthrough при `PII_ENC_KEYS=None`).
- ✅ SQLAlchemy `TypeDecorator`: `EncryptedString` (sentinel `gAAAAA` prefix), `EncryptedJsonb` (wrap pattern `{_encrypted: true, ciphertext: ...}`), `EncryptedBytea`. Transparent encrypt/decrypt на ORM-уровне — mapper'ы и rules engine не trogал.
- ✅ 6 PII колонок encrypted: `analysts.full_name` (500), `analysts.mfa_secret` (200, closes CA-DS12), `borrowers.director_name` (500), `borrower_snapshots.payload` (JSONB), `drafts.payload` (JSONB), `gnk_certificates.file_bytes` (BYTEA).
- ✅ `audit_log` emails masked через shared `infrastructure/auth/email_mask.py` (3 callsites: mfa.py, authenticate_analyst.py, admin.py).
- ✅ Alembic `c5d2f3a7e1b4`: schema length expansions + data encrypt pass. Idempotent (sentinel skip). Downgrade decrypt'ит обратно через тот же ключ. Без `PII_ENC_KEYS` — schema-only.
- ✅ Production startup-assertion в `interfaces/api/app.py`: `app_env in ("staging","prod") + not pii_enc_keys → RuntimeError`.
- ✅ Backward-compat: TypeDecorator читает legacy plain values (без sentinel) as-is, чтобы rollout кода до миграции работал.
- ✅ Tests: 5 unit (Null) + 8 unit (Fernet rotation/invalid/empty) + 9 unit (TypeDecorator backward-compat) + 5 unit (email_mask) + 6 integration (testcontainers raw SELECT vs ORM SELECT roundtrip).
- ✅ Runbook `docs/operations/pii-key-rotation.md`: key generation, rotation deploy steps, pre-migration pg_dump policy, recovery from key loss.
- ⏳ Vault / KMS integration — deferred в T4 compliance phase.

ИНН + name ЮЛ + addresses + red_flags + audit-log non-email keys оставлены plain (публичные / search-critical / list-view perf / уже masked).

### T1.4 — Multi-tenant runtime isolation ✅ DONE 2026-05-18

Approach A pure (single-tenant per deployment) — scope сужен после PROJECT_BRIEF Sec 11 review. Каждый банк = отдельный compose-project с отдельным Postgres-volume; brand_id колонки в data-tables НЕ добавляются (out of scope, см. ADR-0018).

3 коммита:
- `44c42a6` **T1.4.1**: `Settings.brand_id` + `_validate_runtime_config` helper в `app.py` (BRAND_ID resolves в `config/brands/<id>.json` или RuntimeError + PII_ENC_KEYS prod-mandatory, обобщает inline check из T1.3). `load_brand(brand_id)` mandatory arg, env-fallback внутри loader убран. PDF endpoint партиал-биндит `settings.brand_id` через `partial(load_brand, brand_id)`. ADR-0018 «Multi-tenant runtime isolation (Approach A)». 6 unit-тестов на `create_app` startup-validation.
- `80e8cfc` **T1.4.2**: `audit_log.brand_id VARCHAR(50) NOT NULL DEFAULT 'default'` + index `(brand_id, created_at)`. Alembic `e7f9a3c2b8d1`, backfill 'default' для existing rows, down/up roundtrip verified. Repository конструктор принимает brand_id; 5 callsites пробрасывают `settings.brand_id` (DI factory `get_audit_log_repo` + shared/dossier × 2 + dossier_pdf + bank/search). 3 новых integration на repo round-trip.
- `<this commit>` **T1.4.3**: `docs/operations/multi-tenant-deploy.md` playbook + roadmap status sync + CLAUDE.md current status.

**Acceptance:** 2 compose-project'а на одной dev-машине (`credit-default` + `credit-uzbekbank`) с offset-портами (`8000`/`8001`, `5433`/`5434`, `6379`/`6380`), separate volumes, separate `.env`. Запросы изолированы на network-level и DB-level. Live-browser smoke на двух одновременных инстансах — не выполнен в этой Windows-сессии (отдельный заход через `docker compose -f` override).

**Heads-up:** brand_id в data-tables (`borrowers/dossiers/snapshots/drafts/analysts`) НЕ добавлен — out of scope для Approach A. Если future shared-DB требование появится — отдельный таск с миграцией + middleware. См. ADR-0018 «Out of scope» section.

### T1.5 — LDAP AuthnAdapter (CA-020 LDAP-part) ✅ DONE 2026-05-18

LDAP-only scope (OAuth defer'ится в T1.5b). 3 атомарных коммита:

- `dec6332` **T1.5.1**: Settings (`AUTHN_MODE`, `LDAP_*`, `ADMIN_BREAK_GLASS_EMAILS`) + `LdapAuthnAdapter` + `Ldap3Client` (ldap3 pure Python, async via `to_thread`) + `BreakGlassAuthnAdapter` (email whitelist → seeded). 14 unit tests (mock-based). ADR-0019.
- `9c43245` **T1.5.2**: Alembic `f4a2d6c9e3b8` — `analysts.password_hash` NULLABLE + `authn_source` column + CHECK constraint. `analyst_repo.upsert_from_ldap()` для lazy provisioning. DI factory switch в `get_authn_adapter`. `_validate_runtime_config` extended на LDAP-config validation. `change-password` endpoint блокируется для LDAP-users (`password_hash IS NULL`). 3 новых integration test'а.
- `<this commit>` **T1.5.3**: `AuthnPort.authenticate` теперь возвращает `AuthnResult(identity, source)`. `authn_source` в audit-log login payload для compliance trail (`seeded`/`ldap`/`break_glass`). Playbook `docs/operations/ldap-setup.md`. Status sync.

**Acceptance:**
- `AUTHN_MODE=seeded` (default) — никаких изменений в поведении, существующие dev/staging deployments работают.
- `AUTHN_MODE=ldap` без `LDAP_*` env → RuntimeError на boot.
- `AUTHN_MODE=ldap` с полным env: non-whitelist email → LDAP bind+search → lazy upsert; whitelist email → seeded bcrypt; audit-log пишет правильный source.
- 1034 pytest passed, ruff/mypy strict clean.

**Heads-up:** mock-only unit tests — openldap testcontainer defer'ится в **T1.5c** backlog. Production smoke на bank-инсталляции делается с реальным AD. Также: live-browser smoke (login flow через UI в ldap-mode) не выполнен в Windows-сессии без LDAP-сервера. См. ldap-setup.md migration checklist.

---

## Tier 2 — Data quality

- ~~**T2.1** — Dynamic unit detection FORM_2 + FORM_1 (CA-028)~~ → ✅ **DONE 2026-05-18**. 4 атомарных коммитов (helper → FORM_2 wiring → FORM_1 wiring → docs sync). Helper `parse_unit_multiplier` в `header_parser.py`. Scope расширен на FORM_1 (тот же gap). **Heads-up T2.1b backlog:** real-fixture smoke на «млн / полные сум» branches — нет fixture от папы (13/13 = тыс.).
- ~~**T2.2** — VAT parser на реальных 10006_45/10006_47 (CA-015)~~ → **поглощено T0.5 done 2026-05-17 (commit f5d7495)**.
- ~~**T2.3** — PROFIT_TAX parser (CA-029b)~~ → ✅ **DONE 2026-05-18**. 5 атомарных коммитов (parser → dispatch → use-case wiring → cleanup → status sync). Закрывает 5 xfail в `tests/parsers/real_xltx_test.py`, полный 5/5 format coverage парсера. **CA-DS25 sparkline claim снят** — требует monthly_turnover источник (VAT_DECL chain / ESF), не PROFIT_TAX.
- ~~**T2.4** — faktura.uz integration (CA-DS11)~~ → ✅ **DONE 2026-05-18 as honest stub** (ADR-0020). Реальный client → T2.4b backlog (pre-condition: пилот-банк даёт OAuth-токен).

---

## Tier 3 — Operational readiness (после T2)

**Tier 3 / T3.2 (2026-05-18):** ✅ **closed**. Structured logging + correlation_id. Foundation для T3.1/T3.3/T3.5. 4 атомарных коммита: T3.2.1 stdlib bridge (`structlog.stdlib.ProcessorFormatter` + `setLogRecordFactory` global hook + idempotent `_CONFIGURED` guard) · T3.2.2 `RequestIDMiddleware` (X-Request-ID echo/auto-gen 32-hex + bind/unbind contextvars) · T3.2.3 wire в `create_app` outer (LIFO) + instrumental log в health endpoint · T3.2.4 `audit_log.request_id VARCHAR(32) NULL` колонка + index (Alembic `a7c1e4d8b3f5`) + repo читает из contextvars best-effort. Forensics: `SELECT * FROM audit_log WHERE request_id = 'xxx'` дотягивает полный сюжет инцидента. Decisions (defaults): header `X-Request-ID` (Heroku/AWS), `uuid4().hex`, echo always, audit_log.request_id включён в scope (natural fit). Tests: 4 unit (logging) + 5 unit (middleware) + 4 integration in-src + 2 integration testcontainers. План — `docs/superpowers/plans/2026-05-18-t32-correlation-id.md`.

**Tier 3 / T3.3 (2026-05-18):** ✅ **closed**. Prometheus /metrics + Grafana dashboard pack (ADR-0023). 4 атомарных коммита. Backend `prometheus-fastapi-instrumentator` (auto HTTP histogram/counter/gauge) + 3 custom (pdf_render_duration histogram, parser_warnings_total{format}, red_flags_fired_total{severity}). `Settings.metrics_enabled=False` default off. `docker-compose.metrics.yml` opt-in (Prometheus 9090 + Grafana 3001 с auto-provisioning). Bundled dashboard 7 panels (request rate / error rate / latency p50/p95/p99 / PDF p50/p95 / parser warnings / red flags / inflight). Wire в call-sites через lazy imports (WeasyPrintPdfRenderer.render time histogram / dossier handler red flags counter / parse_manual_input_files warnings counter). Playbook `docs/operations/metrics.md` (9 sections включая cross-reference event↔log↔metric через request_id). **Tier 3 fully closed (6/6 items).**

**Tier 3 / T3.1 (2026-05-18):** ✅ **closed**. Observability via GlitchTip on-prem (ADR-0022). 4 атомарных коммита (+1 lock-fix). Sentry SaaS forbidden (PROJECT_BRIEF Sec 8) → GlitchTip OSS Sentry-compat. Backend: `sentry-sdk[fastapi]` + `init_sentry` ДО `configure_logging` + custom `_before_send` PII scrubber (drops request body/cookies, scrubs secret-like keys, masks emails). Frontend: `@sentry/nextjs` + `instrumentation.ts`/`-client.ts` + `error.tsx` boundary с `captureException`. `replaysSessionSampleRate=0` — banking UI privacy. `request_id` tag в `RequestIDMiddleware` (cross-ref event ↔ log из T3.2). `docker-compose.observability.yml` opt-in (4 контейнера postgres/redis/django/celery). Decisions: GlitchTip / `traces_sample_rate=0` / PII scrubbing 2 уровня / `SENTRY_DSN=None` default off / global tags brand_id+app_mode+app_env / `withSentryConfig` отложен (sourcemaps upload требует release pipeline post-demo). Playbook `docs/operations/observability.md`. **Tier 3 — 5 из 6 closed.**

**Tier 3 / T3.6 (2026-05-18):** ✅ **closed**. On-prem tarball deploy. 5 атомарных коммитов. ADR-0021 (alternatives rejected: registry-pull / Ansible / K8s / apt-repo). `web/Dockerfile` (Next.js standalone) + `next.config.ts` `output:"standalone"`. `deploy/install.sh` (preflight → .env validation → docker load → systemd install + enable + wait /health). `deploy/.env.example` / `Caddyfile.template` / `systemd/*.service` + `*.timer` / `docker-compose.prod.yml` override (Caddy reverse-proxy 80/443, postgres/redis без host-portов). `scripts/build_release_tarball.sh` — bundles credit-assistant-vX.Y.Z.tar.gz (5 docker save -gz images + source + deploy + SHA256, ~600 MB - 1.5 GB). `deploy/README.md` "0 → running" walkthrough <30 мин. Decisions (defaults): bundled tarball / Caddy reverse-proxy / Docker compose + systemd / install.sh bash / `.env` validation fail-fast / secrets NOT in tarball (Vault). **Tier 3 — все 3 deal-breaker'а closed (T3.2 + T3.4 + T3.6).**

**Tier 3 / T3.4 (2026-05-18):** ✅ **closed**. Postgres backup + restore drill. 4 атомарных коммита. `scripts/backup_postgres.sh` (bash, pg_dump --format=custom --compress=9 + retention + opt-in age encryption через `BACKUP_AGE_RECIPIENT`). `scripts/restore_drill.sh` (pg_restore latest в temp DB → COUNT(*) per table diff < DRILL_ROW_DIFF_PCT default 5%; cleanup через trap EXIT). `docker-compose.backup.yml` override — sidecar `db-backup` postgres:16-alpine + dcron + age. Playbook `docs/operations/db-backup.md` — 3 prod destinations (A local / B NFS / C S3 MinIO) + encryption setup (age-keygen + Vault) + disaster scenarios + restore drill systemd timer weekly. Decisions (defaults): bash скрипт / Docker sidecar / pg_dump custom format / age opt-in / 7d dev + 30d prod / restore drill обязателен. Tests: 3 backup + 3 restore drill (testcontainers, **passed в CI** — ubuntu-latest runner имеет Docker + pg_dump preinstalled). Hotfix `ffc3b42` для Windows-Docker compat: bash sleep-loop вместо dcron, busybox `find` → `ls -t` fallback, exec-bit на скрипты через `git update-index --chmod=+x`.

**Tier 3 status (2026-05-18): ✅ fully closed (6/6).** Все items — T3.1
observability / T3.2 correlation_id / T3.3 metrics / T3.4 backup / T3.5
audit-export / T3.6 on-prem tarball — закрыты в одной сессии.
Pre-demo MVP ready.

---

## Tier 4 — Compliance pack (параллельно с T1–T3, начать за 2 мес до подачи)

- **T4.1** — Penetration test от лицензированной узб-лаборатории (есть несколько вендоров — выбрать после консультации с банковским procurement). Отчёт нужен для tender package.
- **T4.2** — Аттестат соответствия УзСтандарта на обработку ПДн (Закон РУз «О персональных данных» №547). Процесс 2–3 месяца, нужны documented procedures.
- **T4.3** — Резидентство в IT-юрисдикции РУз (IT Park / Uzinfocom) — закупочное требование госбанков.
- **T4.4** — Документация: Admin Guide · Security Architecture · DRP/BCP. Каждый документ — RU + UZ, PDF, версионирование в git.

---

## Заблокированные (pre-condition не выполнен)

- **CA-DS18c** formatCaseId year edge — pre-condition: T1.1 + `useFormDraft` пробрасывает `draft.created_at`. Замыкается одновременно с T1.1.
- **CA-DS25** KPI sparkline — pre-condition: monthly_turnover≥12 источник (VAT_DECL chain monthly sequence или ESF monthly aggregation). **Не закрыт T2.3 PROFIT_TAX** — корректировка от 2026-05-18 после анализа kpi_calculator (sparkline формируется из monthly chunks, PROFIT_TAX даёт только annual). Frozen до пост-демо.
- **CA-DS28** ГНК public lookup (CA-003 Phase B) — pre-condition: legal review закрыт.
- ~~**CA-029b full scope**~~ → ✅ DONE 2026-05-18 (T2.3).

---

## Backlog (вне Roadmap, могут не понадобиться)

- **CA-015b** — VAT-парсер для следующих xltx-форматов сверх T0.1 пакета. Оценить после T0.1.
- **T2.4b** — faktura.uz real client integration (ADR-0020 implementation reference). Pre-condition: пилот-банк предоставил OAuth-токен для тестового ЮЛ. Scope: `infrastructure/external/faktura_client.py` + `esf_repository.py` + `esf_service.py` + endpoint, fallback chain env → DB → live → cached → static, переиспользует ADR-0014 pattern (4-5 коммитов как T0.2 / T0.3). При активации tip /api/system/health и frontend badge `not_implemented` → `ok` для faktura_uz.
- **CA-DS11b** — faktura.uz расширенный scope (queries, history). Оценить после T2.4b real client.
- **T1.5b** — OAuth2/OIDC AuthnAdapter. Pre-condition: запрос от пилот-банка на Okta/Azure AD интеграцию. Реализация поверх существующего `AuthnPort` (как `LdapAuthnAdapter`), library `authlib`. ADR-0019b.
- **T1.5c** — openldap testcontainer для full integration tests `LdapAuthnAdapter`. Текущее покрытие — mock-only (`MagicMock(spec=LdapClient)`). Hardening pass с реальным `osixia/openldap` контейнером.
- **T2.1b** — real-fixture smoke на FORM_2 / FORM_1 с «млн. сум.» либо «сум.» (полные) единицами измерения. Текущее покрытие — synthetic factory only (10 unit-кейсов TestUnitMultiplier). 13/13 real fixtures от папы = «тыс. сум.» (no signal of variance). При появлении нестандартного xltx — добавить в `tests/fixtures/soliq_xltx/` + ассерты multiplier branches в `real_xltx_test.py`. Pre-condition: получить такой файл (например от крупной фирмы с «млн. сум.» или мелкой с полными «сум.»).
- **CA-DS30** — anonymize gap для real xltx fixtures. Сейчас 1/28 `*_anon.xltx` на месте. Bulk anonymization через openpyxl script: per-format (VAT_DECLARATION / VAT_REGISTRY_ILOVA / FORM_2 / FORM_1 / PROFIT_TAX) replace правил для ИНН (на dummy ИНН) / имён (синтетика) / сумм (random preserving order-of-magnitude + signature-cells для parser format-detection). Скрипт `scripts/anonymize_xltx.py` + 28 anonymized output → git. **Post-T1 priority** (после T1.1-T1.5 prod-killers).
