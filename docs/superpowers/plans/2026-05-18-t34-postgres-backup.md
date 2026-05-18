# T3.4 — Postgres backup + retention + restore drill

> Deal-breaker для on-prem demo: bank-IT first question — «как восстановиться
> после краша». Без drill-script отвечать нечего.

## Decisions (approved 2026-05-18, defaults)

- **Script language**: Bash. `pg_dump`/`pg_restore` идут в postgres image,
  никаких extra deps. Bank-IT привычен.
- **Scheduler**: Docker sidecar (cron в `postgres:16-alpine`) для dev/staging.
  Prod-инструкция в playbook — на выбор systemd-timer либо тот же sidecar.
- **Format**: `pg_dump --format=custom --compress=9` (custom = supports parallel
  restore через `pg_restore -j`, compress=9 — gzip level 9 inside dump).
- **Backup file encryption**: opt-in через `BACKUP_AGE_RECIPIENT` env. age
  (filippo.io/age) — modern asymm encryption, single binary, no keyring. Default
  off в dev, on в prod через playbook + Vault recipient.
- **Retention**: 7d dev (env `BACKUP_RETENTION_DAYS=7`), 30d prod.
- **Restore drill**: отдельный `restore_drill.sh` — pg_restore latest dump в
  `<db>_drill_<ts>` temp DB → row counts vs source → drop temp. Exit 0 = PASS.
- **Dev destination**: host bind `./backups/` (gitignored).
- **Prod destinations** (playbook 3 опции): A local volume / B NFS mount /
  C MinIO push (S3-compat).

## Out of scope

- WAL streaming / PITR — overkill для daily-snapshot use-case; вернёмся в T4
  compliance (если pentest потребует).
- Cross-region replication — bank внутренняя decision.
- Backup integrity verification через сравнение хешей — restore_drill покрывает
  главное (структурная целостность + non-empty).
- Off-site shipping (rclone / rsync) — playbook упоминает как опцию C, скрипт
  не реализует (банк подключит свой transport).

## Encryption story

PII-столбцы уже зашифрованы T1.3 Fernet — ciphertext попадает в dump as-is.
Все остальные данные (search-keys, ИНН, public registry rows) plain. Поэтому:

- Local volume + filesystem permissions (660 owner=postgres) — достаточный
  threat model для dev и для бank-local SAN.
- NFS / off-site / removable media → нужен app-level encryption поверх dump.
  age с recipient public key из банковского Vault.

## Atomic split

### T3.4.1 — backup_postgres.sh + retention + tests (~5 файлов)

**Файлы:**
1. `scripts/backup_postgres.sh` — main script:
   - Env: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `BACKUP_DIR`
     (def `/var/backups/credit-assistant`), `BACKUP_RETENTION_DAYS` (def 7),
     `BACKUP_AGE_RECIPIENT` (optional).
   - `set -euo pipefail`; UTC timestamp `YYYYMMDDTHHMMSSZ`.
   - `pg_dump --format=custom --compress=9 --no-owner --no-acl` → temp file →
     если AGE → `age -r $RECIPIENT -o <name>.dump.age` иначе rename в `.dump`.
   - Retention: `find $BACKUP_DIR -name "*.dump*" -mtime +$RETENTION -delete`.
   - Stderr-logging формат `[ISO_TS] [level] message` (systemd journal compat).
   - Exit codes: 0 ok / 10 pg_dump fail / 11 encryption fail / 12 retention fail.
2. `tests/integration/scripts/backup_postgres_test.py` — testcontainers postgres:
   - `test_backup_creates_dump_file` — после run появляется `*.dump` non-empty.
   - `test_backup_retention_removes_old_files` — touch два fake-dump'а с mtime
     -10d → script удаляет один (старше 7).
   - `test_backup_fails_loudly_on_pg_dump_error` — bad credentials → exit 10.
   - (опционально) `test_backup_encrypts_with_age_recipient` — если age
     установлен в test env, проверить `.dump.age` существует + начало байтов
     `age-encryption.org/v1`. Skip если no age.
3. `scripts/backup_postgres_test.sh` — bash syntax check (`bash -n`) + smoke
   через `pg_dump --version` — паранойя на parse-fail.
4. `.gitignore` — добавить `backups/`.
5. (опционально) `scripts/backup_age_keygen.sh` — wrapper для `age-keygen -o
   key.txt` с инструкцией не коммитить.

**TDD цикл:**
- Red 1: `test_backup_creates_dump_file` — script не существует, FileNotFound.
- Green 1: minimal script с pg_dump + tempfile rename.
- Red 2: `test_backup_retention_removes_old_files` — нет retention logic.
- Green 2: добавить `find -mtime`.
- Red 3: `test_backup_fails_loudly_on_pg_dump_error` — без `set -e` exit 0.
- Green 3: добавить `set -euo pipefail` + специфический exit codes.

**Verify:**
```bash
bash -n scripts/backup_postgres.sh
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest tests/integration/scripts/backup_postgres_test.py -v"
```

**Commit:** `feat(ops): T3.4.1 pg_dump backup script + retention`.

---

### T3.4.2 — restore_drill.sh + integration test (~2 файла)

**Файлы:**
1. `scripts/restore_drill.sh`:
   - Find latest `*.dump` в `$BACKUP_DIR` (newest mtime).
   - Декрипт если `.dump.age` (требует `AGE_IDENTITY` env path к private key).
   - `createdb` temp database `<PGDATABASE>_drill_<ts>` (через `PGUSER`).
   - `pg_restore -d <temp_db> -j 4 --no-owner --no-acl <dump>`.
   - Row counts: `SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY 1`
     на обоих БД → diff.
   - Threshold: max 5% rows diff (write-during-backup tolerance) → PASS, иначе
     FAIL.
   - Drop temp DB unconditional (cleanup в `trap`).
   - Exit 0 PASS / 20 restore fail / 21 row-count mismatch / 22 cleanup fail.
2. `tests/integration/scripts/restore_drill_test.py` — testcontainers:
   - `test_drill_passes_on_fresh_backup` — pg_dump + restore_drill в той же
     testcontainer → exit 0.
   - `test_drill_fails_on_corrupted_dump` — touch fake `*.dump` (0 bytes) →
     pg_restore fail → exit 20.

**TDD цикл:**
- Red: `test_drill_passes_on_fresh_backup` — script ещё нет.
- Green: minimal restore_drill.
- Red: `test_drill_fails_on_corrupted_dump` — exit 0 на пустом dump.
- Green: добавить strict pg_restore + exit guards.

**Verify:** `bash -n scripts/restore_drill.sh` + integration test.

**Commit:** `feat(ops): T3.4.2 restore drill script + row-count verification`.

---

### T3.4.3 — Docker sidecar + playbook (~3 файла)

**Файлы:**
1. `docker-compose.backup.yml` (override):
   - service `db-backup` — image `postgres:16-alpine`, depends_on postgres healthy.
   - mount `./scripts:/scripts:ro` + `./backups:/var/backups/credit-assistant`.
   - entrypoint: install `dcron` + age (apk add) + crontab `0 2 * * * /scripts/backup_postgres.sh`.
   - env: `PGHOST=postgres`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, etc.
2. `docs/operations/db-backup.md` — playbook:
   - **Section 1**: Architecture (что бэкапится / что не бэкапится / encryption story).
   - **Section 2**: Dev setup (`docker compose -f docker-compose.yml -f docker-compose.backup.yml up -d`).
   - **Section 3**: Manual operations (run backup now / list backups / decrypt).
   - **Section 4**: Restore drill (run + schedule + alerting on FAIL).
   - **Section 5**: Prod destinations:
     - **A — local volume**: simplest, off-host risk при крахе host.
     - **B — NFS mount**: банк-IT даёт remote share, mount в `BACKUP_DIR`.
     - **C — S3-compat (MinIO)**: post-backup rclone push, retention на bucket.
   - **Section 6**: Encryption setup (age keygen + Vault для recipient + identity).
   - **Section 7**: Recovery from key loss (restore-pre-T1.3 backup pattern).
   - **Section 8**: Disaster scenarios + RPO/RTO (daily backup → max 24h loss; restore
     ~minutes для <10GB db).
3. `compose.yml` — комментарий с pointer на backup override.

**TDD цикл:** no functional tests (deploy artifact); проверка через manual `docker
compose ... up -d db-backup` + `docker compose exec db-backup /scripts/backup_postgres.sh`.

**Verify:**
```bash
docker compose -f docker-compose.yml -f docker-compose.backup.yml config  # syntax
```

**Commit:** `docs(ops): T3.4.3 backup sidecar compose override + playbook`.

---

### T3.4.4 — Docs sync (~2 файла)

**Файлы:**
1. `CLAUDE.md` — Current Status новая запись T3.4 closed + tick.
2. `docs/pre-demo-roadmap.md` — Tier 3 status section.

**Commit:** `docs(internal): T3.4 backup story closure`.

---

## Verify (full)

После каждого atomic commit:
```bash
PYTHONPATH=src uv run --no-sync python -m ruff check . && \
  uv run --no-sync python -m mypy --strict src/ tests/ && \
  bash -n scripts/backup_postgres.sh scripts/restore_drill.sh
```

CI прогонит integration через testcontainers — локально Docker может быть offline.

## Estimate

- T3.4.1 backup script + tests — 2h
- T3.4.2 restore drill — 1.5h
- T3.4.3 compose + playbook — 1.5h (playbook самый трудоёмкий)
- T3.4.4 docs — 0.5h

**Total: ~5.5h.**

## Risks / open subtleties

- **pg_dump version mismatch**: backup-container postgres 16-alpine dump'ит в БД
  postgres 16 — fine. Если кто-то обновит DB до 17, sidecar тоже надо bump.
  Playbook упоминает.
- **age binary не в alpine apk**: проверить. Если нет — `apk add age` через
  community repo либо manual download в Dockerfile. Worst case — отдельный
  Dockerfile для backup-sidecar с FROM postgres:16-alpine + age install.
- **Restore drill row-count threshold 5%**: на пустой dev-БД 0 rows у всех
  таблиц → 0% diff, fine. На write-heavy prod backup идёт ~30s, rows могут
  драифтнуть. Threshold 5% — эмпирический; в playbook упомянуть что увеличивать
  если PASS false-fail'ит.
- **Encrypted backup size**: age добавляет ~256B overhead, pretty much neglible.
- **Backup time = downtime?**: `pg_dump` не блокирует writes (uses MVCC snapshot),
  но heavy IO load на host. Для prod планировать на низкий-traffic окно (03:00
  Asia/Tashkent).
- **Permissions on `BACKUP_DIR`**: sidecar пишет как root, host видит как root.
  Playbook упоминает chmod 660 + chown postgres:postgres для production.
