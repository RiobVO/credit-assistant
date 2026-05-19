# Credit Assistant — on-prem deploy guide

> Target: «0 → running» за <30 минут на чистом Linux-хосте с Docker.
> Bundled tarball, zero-internet install, systemd-managed lifecycle.
> См. ADR-0021 для архитектурного контекста.

---

## 1. Preconditions

**Hardware:**

* x86_64 Linux (Ubuntu 22.04 LTS / 24.04 LTS / Debian 12 / RHEL 9 — tested).
* CPU ≥ 2 cores, RAM ≥ 4 GB, disk ≥ 20 GB.
* Сеть с открытыми портами 80, 443 для analyst-traffic.

**Software preinstalled:**

* Docker Engine ≥ 24 (`docker --version`).
* Docker Compose plugin (`docker compose version`).
* `tar`, `gzip`, `systemctl`.
* `curl` (для verification).
* `openssl` (для generation секретов).

**Privileges:**

* root либо sudo-доступ для копирования systemd-юнитов и `/opt/` записи.
* Доступ к банк-Vault для secrets (PII_ENC_KEYS, JWT_SECRET, LDAP creds).

---

## 2. Extract + secrets

```bash
# Распаковка в /opt/credit-assistant.
sudo tar xzf credit-assistant-vX.Y.Z.tar.gz -C /opt/

# Verify checksum (anti-tamper).
sha256sum -c credit-assistant-vX.Y.Z.tar.gz.sha256

cd /opt/credit-assistant
sudo cp deploy/.env.example .env
sudo chmod 600 .env
sudo nano .env   # отредактировать секреты
```

Минимальный список секретов перед `install.sh`:

| Var | Source | Validate |
|---|---|---|
| `JWT_SECRET` | `openssl rand -base64 48` | ≥32 chars |
| `POSTGRES_PASSWORD` | banking Vault или `openssl rand -base64 24` | not CHANGE_ME |
| `PII_ENC_KEYS` | banking Vault (T1.3) | Fernet key 44 chars |
| `BRAND_ID` | `config/brands/<id>.json` доступен | resolves |
| `CADDY_DOMAIN` | DNS банка | reachable |
| `AUTHN_MODE` | `seeded` для pilot / `ldap` для prod | enum |
| `LDAP_*` | banking AD ops (если ldap) | all required |

**PII_ENC_KEYS generation:**

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → положить в банк-Vault, инжектить в .env
```

`.env` файл должен быть chmod 600 owner root.

---

## 3. Run installer

```bash
sudo /opt/credit-assistant/deploy/install.sh
```

Что делает скрипт:

1. **Preflight**: проверяет root, docker, tar, gzip, systemctl, compose plugin.
2. **`.env` validation**: JWT_SECRET ≥32 chars, PII_ENC_KEYS не пуст в
   staging/prod, BRAND_ID резолвится в `config/brands/<id>.json`, LDAP_* —
   если AUTHN_MODE=ldap. Fail-fast при пустых обязательных значениях.
3. **`docker load`** для каждого `images/*.tar.gz` (api, web, caddy, postgres, redis).
4. **systemd units**: копирует `credit-assistant.service` +
   `credit-restore-drill.{service,timer}` в `/etc/systemd/system/` +
   `daemon-reload`.
5. **enable + start**: `systemctl enable --now credit-assistant`.
6. **enable weekly drill timer**: Sun 04:00 Asia/Tashkent.
7. **wait for /health**: до 90s после старта, либо отчёт об ошибке.
8. Печатает onboarding-инструкцию (URL, seed admin command, log paths).

Время install — обычно 2-5 минут (docker load — самая медленная фаза).

---

## 4. Verify

```bash
# Health через Caddy (HTTPS):
curl -fsSL https://${CADDY_DOMAIN}/health

# Backend health напрямую (если Caddy не справился):
docker exec credit-api curl -fsS http://127.0.0.1:8000/health

# Frontend проверка:
curl -fsSL https://${CADDY_DOMAIN}/  # должен вернуть HTML с Next.js bundle.

# Логи всей системы:
journalctl -u credit-assistant -n 100 -f

# Compose-сервисы:
docker compose -f /opt/credit-assistant/docker-compose.yml \
  -f /opt/credit-assistant/docker-compose.prod.yml ps
```

**Seed первого аналитика** (после успешного health-check):

```bash
docker compose -f /opt/credit-assistant/docker-compose.yml \
  -f /opt/credit-assistant/docker-compose.prod.yml \
  exec api bash -c "cd /app/src && uv run --no-sync python -m \
  interfaces.cli.seed_analysts --email admin@bank.uz \
  --password 'CHANGE_ME_strong_pw' --full-name 'Admin Analyst' \
  --role senior_analyst"
```

Login: `https://${CADDY_DOMAIN}/login` → email + password → MFA enrollment
(см. 2FA smoke playbook `docs/operations/2fa-smoke.md`).

---

## 5. Upgrade procedure

1. Получить новый `credit-assistant-vX.Y.Z.tar.gz` + `.sha256`.
2. **Backup**: ensure последний restore_drill PASS.
   ```bash
   sudo systemctl start credit-restore-drill.service
   journalctl -u credit-restore-drill -n 50
   ```
3. **Stop**: `sudo systemctl stop credit-assistant`.
4. **Extract** новый tarball поверх (overwrites `src/`, `deploy/`, `docs/`;
   pgdata/redisdata/caddy_data volumes остаются):
   ```bash
   sudo tar xzf credit-assistant-vX.Y.Z.tar.gz -C /opt/
   ```
5. **Save `.env`**: обычно остаётся (overwrite на `.env.example`, не `.env`).
   Verify: `diff /opt/credit-assistant/.env /opt/credit-assistant/.env.example`.
   Новые env-keys из `.env.example`, отсутствующие в `.env`, добавить вручную.
6. **Re-run install.sh**: загрузит новые images, переустановит systemd unit,
   restart stack. Migrations apply через `api` entrypoint автоматически.
7. **Verify** (см. Section 4).

Время upgrade — обычно 5-10 минут.

---

## 6. Troubleshooting

### `install.sh` reports "Missing required .env values: X"

Заполнить недостающие переменные в `/opt/credit-assistant/.env`,
повторить `install.sh`.

### Caddy can't bind 443 — port in use

```bash
sudo ss -ltnp | grep :443
# найти конкурента (nginx/apache?), stop его или поменять CADDY_DOMAIN
# на subdomain с другим портом.
```

### Migrations fail на старте

```bash
docker compose ... logs api | tail -50
# часто: PII_ENC_KEYS не задан, либо Alembic не может connect к postgres.
```

Recovery: проверить `.env`, restart `credit-assistant`. Если data corruption —
restore из backup (см. `docs/operations/db-backup.md` Section 7).

### Docker images не загружаются (`docker load` fails)

* Disk space: `df -h /var/lib/docker/`. Нужно ≥ 5 GB free.
* Verify SHA256: `sha256sum -c credit-assistant-vX.Y.Z.tar.gz.sha256`.

### `journalctl -u credit-assistant` показывает старт-перезапуски

```bash
docker compose -f /opt/credit-assistant/docker-compose.yml \
  -f /opt/credit-assistant/docker-compose.prod.yml \
  logs -f
```

Чаще всего: api падает на startup-assertion — см. `_validate_runtime_config`
в `interfaces/api/app.py` (BRAND_ID / PII_ENC_KEYS / LDAP_*).

### LDAP authentication fail после AUTHN_MODE=ldap

См. `docs/operations/ldap-setup.md` — generic AD defaults, ldap3 connection
tests.

---

## 7. Uninstall

### Soft (keep data, для miграции на другой host)

```bash
sudo systemctl disable --now credit-assistant credit-restore-drill.timer
sudo rm /etc/systemd/system/credit-assistant.service \
        /etc/systemd/system/credit-restore-drill.{service,timer}
sudo systemctl daemon-reload
# pgdata/redisdata/caddy_data volumes остаются.
docker compose -f /opt/credit-assistant/docker-compose.yml \
  -f /opt/credit-assistant/docker-compose.prod.yml down
```

### Hard (data loss — для wipe deploy)

```bash
sudo systemctl disable --now credit-assistant credit-restore-drill.timer
docker compose -f /opt/credit-assistant/docker-compose.yml \
  -f /opt/credit-assistant/docker-compose.prod.yml down -v   # -v убивает volumes
docker rmi credit-api:* credit-web:* caddy:2-alpine \
           postgres:16-alpine redis:7-alpine
sudo rm -rf /opt/credit-assistant
sudo rm /etc/systemd/system/credit-assistant.service \
        /etc/systemd/system/credit-restore-drill.{service,timer}
sudo systemctl daemon-reload
```

**Внимание:** hard uninstall безвозвратно теряет audit_log + borrower data.
Перед прогоном — обязательный backup. См. `docs/operations/db-backup.md`.

---

## 8. References

* ADR-0021 — on-prem tarball deploy architecture decision.
* `docs/operations/pre-demo-smoke.md` — обязательный live-browser smoke перед demo trip.
* `docs/demo/scenarios.md` — 5 заранее подготовленных borrower-сценариев для walkthrough.
* `docs/operations/db-backup.md` — backup + restore drill (T3.4).
* `docs/operations/pii-key-rotation.md` — PII_ENC_KEYS lifecycle (T1.3).
* `docs/operations/ldap-setup.md` — LDAP authentication setup (T1.5).
* `docs/operations/multi-tenant-deploy.md` — несколько банков на одной машине (T1.4).
* `docs/operations/2fa-smoke.md` — MFA enrollment walkthrough.
* `deploy/install.sh` / `deploy/.env.example` — installer + template.
* `scripts/build_release_tarball.sh` — release artifact builder.
