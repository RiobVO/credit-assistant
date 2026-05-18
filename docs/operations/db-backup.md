# Postgres backup playbook (T3.4)

> Бэкап-стратегия для on-prem банк-инсталляции. Daily snapshots, retention,
> опциональное app-level шифрование (age), automated restore drill.

---

## 1. Архитектура

**Что бэкапится:** все таблицы `credit_assistant` БД через `pg_dump
--format=custom --compress=9 --no-owner --no-acl`.

**Что НЕ бэкапится:**

* Redis (refresh-token denylist) — ephemeral. После restore логины
  пере-авторизуются.
* Загруженные xltx файлы в `./backups/uploaded/` — не используются после
  парсинга (snapshot.payload содержит результат).
* PII-столбцы остаются **зашифрованными** в dump'е (T1.3 / ADR-0017
  encrypts ON THE COLUMN level через `EncryptedString`/`EncryptedJsonb`).
  Backup-файл сам по себе содержит ciphertext в этих столбцах → для
  чтения нужен `PII_ENC_KEYS`. **Backup без ключа = чистый ciphertext,
  recovery невозможен.**

**Encryption story:**

| Threat | Защита |
|---|---|
| Атакующий читает backup-файл (NFS share, off-site) | age encryption (T3.4 opt-in через `BACKUP_AGE_RECIPIENT`) |
| Атакующий читает БД-disk сразу | T1.3 PII столбцы зашифрованы; non-PII plain (ИНН, public registry) |
| Утеря PII_ENC_KEYS | См. Section 7 — recovery procedure |

**Recovery point objective (RPO):** ≤24h (daily snapshot 02:00 UTC).
**Recovery time objective (RTO):** ~minutes для DB <10 GB
(pg_restore parallel -j 4).

---

## 2. Dev setup

```bash
# Подъём с backup-sidecar (постgres + redis + api + db-backup):
docker compose -f docker-compose.yml -f docker-compose.backup.yml up -d

# Проверка: sidecar поднялся, crontab прописан
docker compose -f docker-compose.yml -f docker-compose.backup.yml \
  logs db-backup | tail
```

Sidecar `credit-db-backup` использует `postgres:16-alpine` image (тот же major
version что и production БД — гарантирует совместимость pg_dump/pg_restore),
устанавливает `dcron` + `age` через `apk add`, прописывает crontab на 02:00 UTC.

Backup-файлы складываются в host-bind `./backups/` (gitignored).

---

## 3. Manual operations

### Запустить backup сейчас (вне расписания)

```bash
docker compose -f docker-compose.yml -f docker-compose.backup.yml \
  exec db-backup /scripts/backup_postgres.sh
```

### Список backup-файлов

```bash
ls -lh ./backups/
# или внутри контейнера
docker compose exec db-backup ls -lh /var/backups/credit-assistant
```

### Decrypt encrypted backup (на хосте, не в контейнере)

```bash
age --decrypt --identity ~/secure/backup-age-identity.txt \
  --output restored.dump ./backups/20260518T020000Z.dump.age
```

### Inspect backup без restore

```bash
docker compose exec db-backup pg_restore --list /var/backups/credit-assistant/20260518T020000Z.dump
```

---

## 4. Restore drill

**Цель:** убедиться что dump-файл валиден и pg_restore полностью отрабатывает,
не повреждая production БД. Запускать **еженедельно** в prod (через cron),
**после каждого major-update** Postgres / схемы.

```bash
docker compose -f docker-compose.yml -f docker-compose.backup.yml \
  exec db-backup /scripts/restore_drill.sh
```

Скрипт:

1. Выбирает newest `*.dump[.age]` в `BACKUP_DIR`.
2. (Если `.age`) декриптует через `AGE_IDENTITY`.
3. Создаёт temp DB `<dbname>_drill_<timestamp>`.
4. `pg_restore -j 4` в temp.
5. Сравнивает row counts на source vs restored. Threshold расхождения
   `DRILL_ROW_DIFF_PCT` (default 5% — write-during-backup tolerance).
6. Drop temp DB (trap EXIT — always).

**Exit codes:**

| Code | Smysl |
|---|---|
| 0 | PASS |
| 20 | pg_restore fail (dump corrupted / version mismatch) |
| 21 | Row count diff exceed threshold |
| 22 | Cleanup fail (temp DB не дропнулась — manual drop) |
| 23 | No backup found |
| 24 | age decrypt fail (wrong identity или corrupted .age) |

**Alerting on FAIL:** в production wire restore_drill в monitoring stack
(когда T3.1 observability будет — Sentry / GlitchTip; пока — cron MAILTO).

### Cron для weekly drill (production systemd-timer)

`/etc/systemd/system/credit-restore-drill.timer`:

```ini
[Unit]
Description=Weekly Postgres restore drill

[Timer]
OnCalendar=Sun 04:00 Asia/Tashkent
Persistent=true

[Install]
WantedBy=timers.target
```

`/etc/systemd/system/credit-restore-drill.service`:

```ini
[Unit]
Description=Run Postgres restore drill

[Service]
Type=oneshot
EnvironmentFile=/etc/credit-assistant/backup.env
ExecStart=/usr/local/bin/credit/restore_drill.sh
StandardOutput=journal
StandardError=journal
```

---

## 5. Production destinations

Onboarding-выбор банка (одно из трёх).

### A — Local volume (default, simplest)

Mount фиксированный SAN/SSD raid:

```bash
mkdir -p /var/backups/credit-assistant
chown postgres:postgres /var/backups/credit-assistant
chmod 0750 /var/backups/credit-assistant
```

В compose / systemd:

```
BACKUP_DIR=/var/backups/credit-assistant
BACKUP_RETENTION_DAYS=30
```

**Risk:** disk-loss host = backup loss. Подходит если SAN raid + off-site
nightly mirror на банк-IT уровне.

### B — NFS mount (off-host)

Банк-IT даёт NFS share. Mount в `fstab`:

```
nfs-bank-storage.internal:/credit-backups /mnt/credit-backups nfs rw,soft,intr 0 0
```

```
BACKUP_DIR=/mnt/credit-backups
BACKUP_RETENTION_DAYS=30
```

**Risk:** NFS-сервер недоступен → cron exit non-zero (alert). encryption настоятельно рекомендуется (NFS visibility).

### C — S3-compatible (MinIO / Ceph RGW)

Сначала backup в local, потом push в bucket. Post-backup hook через
`rclone` (отдельный sidecar или systemd-service `credit-backup-shipper`).

```
BACKUP_DIR=/var/backups/credit-assistant   # staging area
RCLONE_TARGET=minio:credit-backups/<bank-name>/
```

В playbook рекомендация — **always encrypt для S3** (object storage может
быть compromised через credentials leak).

Retention на bucket-level через MinIO lifecycle policy.

---

## 6. Encryption setup (production)

### Сгенерировать age key pair

```bash
age-keygen -o ~/secure/backup-age-identity.txt
# Выведет public key: age1xxx... → копировать в банковский Vault.
```

`backup-age-identity.txt` содержит **private key** — хранить в **банковском
Vault / HSM**, **не на хосте**, **не в git**. На хост-машину инжектится
только при restore-операциях (`AGE_IDENTITY` env).

`backup-age-identity.txt` уже в `.gitignore`.

### Прокинуть recipient в backup env

`.env` или systemd EnvironmentFile:

```
BACKUP_AGE_RECIPIENT=age1xxx...    # public key
```

После этого `backup_postgres.sh` пишет `*.dump.age` вместо `*.dump`.

### Recovery: получить identity для restore

```bash
# На production host (только при инциденте):
cat /run/credit-secrets/backup-age-identity.txt | head  # из mounted secret tmpfs
# или экспортнуть из Vault и положить во временный path:
vault kv get -field=identity secret/credit-assistant/backup-age > /tmp/identity.txt
chmod 600 /tmp/identity.txt
AGE_IDENTITY=/tmp/identity.txt /scripts/restore_drill.sh
shred -u /tmp/identity.txt
```

---

## 7. Disaster scenarios

### Scenario 1: Postgres data-volume corrupted

1. Stop application: `docker compose stop api`.
2. Drop corrupted volume: `docker volume rm credit-assistant_pgdata`.
3. `docker compose up -d postgres` → пустая БД.
4. Find latest valid backup (run drill first):
   ```bash
   ls -t ./backups/*.dump* | head -1
   ```
5. Restore:
   ```bash
   docker compose exec db-backup pg_restore \
     --no-owner --no-acl --jobs=4 \
     -d postgres -C \
     /var/backups/credit-assistant/<file>.dump
   ```
   (`-C` создаёт `credit_assistant` DB заново)
6. Apply latest Alembic migrations: `docker compose run --rm api uv run alembic upgrade head`.
7. Restart api: `docker compose up -d api`.

**Время:** ~5-15 минут на 1-10 GB БД.

### Scenario 2: Loss of PII_ENC_KEYS (T1.3)

См. `docs/operations/pii-key-rotation.md` Section "Recovery from key loss".
Backup без ключа = ciphertext only → шифрованные столбцы (full_name,
director_name, snapshot payload) безвозвратно потеряны. ИНН + основные
борровер-данные plain — частичный recovery возможен.

**Митигация:** `PII_ENC_KEYS` обязан жить в банковском Vault с
multi-recipient access + off-site backup. **Никогда** не хранить только
на одном host'е.

### Scenario 3: Backup file corrupted (drill FAIL)

1. Drill отрапортовал exit 20 или 21.
2. Try previous backup: `ls -t ./backups/*.dump | head -3`.
3. Если несколько подряд corrupted — escalate: проблема с pg_dump или
   с БД consistency.
4. Trigger manual integrity check на source: `VACUUM (ANALYZE, VERBOSE)`.

---

## 8. Operational checklist

**Daily:**

* [ ] `docker compose logs db-backup` без ошибок.
* [ ] `ls -lh ./backups/` показывает свежий файл (~current_size +/- 20%).

**Weekly:**

* [ ] Restore drill PASS.
* [ ] Audit `ls ./backups/` — все ли стоят retention'у; нет ли «забытых».

**Monthly:**

* [ ] Verify off-site replication (если NFS / S3).
* [ ] Check age key rotation due (если policy — 6m / 12m).

**Quarterly:**

* [ ] Full restore drill в clean environment (не temp DB на той же host).
  Подтверждает, что в случае total host-loss восстановление возможно.

---

## 9. Known limitations

* **WAL streaming / PITR** не реализован. RPO=24h. Если бизнес требует
  <1h — добавить WAL-shipping через `pg_basebackup` + `archive_command`
  (T4.5 compliance scope).
* **Cross-region replication** не настроена.
* **Backup encryption через app-layer** (age), **не disk-level**. Disk-level
  encryption (LUKS) — отдельный layer ответственности банк-IT.
* ※ CI testcontainers Docker-job не настроен → `backup_postgres_test.py` и
  `restore_drill_test.py` фактически skipped в текущем CI. Smoke выполняется
  на production deploy и при сетевой dev-prove. Setup Docker-action в
  workflow — отдельная задача T3.x hardening (post-demo).

---

## 10. References

* `scripts/backup_postgres.sh` — main backup script.
* `scripts/restore_drill.sh` — restore drill.
* `docker-compose.backup.yml` — dev sidecar override.
* `docs/operations/pii-key-rotation.md` — PII_ENC_KEYS lifecycle.
* age project — <https://github.com/FiloSottile/age>
* `docs/superpowers/plans/2026-05-18-t34-postgres-backup.md` — план T3.4.
