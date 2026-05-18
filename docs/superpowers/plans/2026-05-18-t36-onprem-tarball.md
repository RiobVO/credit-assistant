# T3.6 — On-prem deploy: bundled tarball

> **Deal-breaker** zero-internet install для узб mid-tier банков (internal
> registry mirror у них обычно нет). `docker save | gzip` + install.sh +
> `db-init.sql.gz` + `.env.example` + systemd unit.

## Decisions (approved 2026-05-18, defaults)

- **Frontend deployment**: bundled Docker image (`node:20-alpine` +
  `next build` + standalone output). Static export невозможен — `cookies()`
  в `layout.tsx` делает все routes dynamic.
- **Reverse proxy**: bundled Caddy 2 для HTTPS-termination (PROJECT_BRIEF
  Sec 3). Mid-tier банки своего reverse-proxy обычно не имеют.
- **Orchestration**: `docker compose` + systemd-unit-обёртка (`docker compose
  up -d` стартует через systemd на boot).
- **Install**: `bash install.sh` — требует `docker` + `tar` + `gzip`
  preinstalled. Валидирует обязательные secrets перед `up`.
- **Tarball name**: `credit-assistant-vX.Y.Z.tar.gz` semver.
- **Extract path**: `/opt/credit-assistant/`.
- **Secrets NOT in tarball**: `PII_ENC_KEYS`, `JWT_SECRET`, `LDAP_*`,
  age private key — оператор инжектит из банк-Vault через `.env`.

## Out of scope

- Каскадные deployments (multi-host) — single-host install.
- Ansible playbook — install.sh покрывает same job для одиночного хоста.
- HA / failover — separate Phase 5+ scope.
- Upgrade-path (rolling update) — first delivery focuses on greenfield
  install. Upgrade описан в README, но automation — backlog.

## Atomic split

### T3.6.1 — Frontend production Docker build (~3 файла)

**Файлы:**
1. `web/Dockerfile` — multi-stage:
   - Stage `deps`: `node:20-alpine` + `npm ci --omit=dev` (только prod deps).
   - Stage `builder`: `npm ci` (с dev для типов) + `npm run build` →
     `.next/standalone` + `.next/static` + `public/` копируются в final.
   - Stage `runner`: `node:20-alpine`, copy standalone, `USER node`,
     `EXPOSE 3000`, `CMD ["node", "server.js"]`.
2. `web/next.config.ts` — добавить `output: "standalone"` для full self-contained
   server.js + минимальная node_modules tree.
3. `web/.dockerignore` — exclude `.next/`, `node_modules/`, `tests/`, etc.

**Verify:**
```bash
docker build -t credit-web:dev ./web
docker run --rm -p 3000:3000 credit-web:dev
curl -sI http://localhost:3000/ | head -1   # → 200
```

**Commit:** `feat(web): T3.6.1 Next.js standalone Dockerfile`.

---

### T3.6.2 — Deploy artifacts: install.sh / .env / Caddy / systemd / compose.prod (~7 файлов)

**Файлы:**
1. `deploy/install.sh` — bash:
   - Preflight: `docker --version`, `tar`, `gzip` available; user privs;
     /opt write permission.
   - Extract tarball в `/opt/credit-assistant/` (если запускается из
     unpacked dir — skip extract).
   - Load Docker images: `docker load -i images/api.tar.gz` × 3 (api / web / caddy).
   - Validate `.env`: `PII_ENC_KEYS` >= 1 ключ × 44 chars; `JWT_SECRET` >= 32 chars;
     `BRAND_ID` resolves в `/opt/credit-assistant/config/brands/<id>.json`;
     `LDAP_*` present если `AUTHN_MODE=ldap`.
   - Init Postgres data dir (если первый install): `docker compose up -d postgres`
     → wait healthy → apply migrations через `api` контейнер (entrypoint.sh
     уже делает).
   - Install systemd unit: `cp deploy/systemd/credit-assistant.service
     /etc/systemd/system/` + `systemctl daemon-reload` + `systemctl enable
     --now credit-assistant`.
   - Print connection info: URL, admin onboarding command.
2. `deploy/.env.example` — все обязательные env с placeholder'ами и
   inline-комментариями: `PII_ENC_KEYS=`, `JWT_SECRET=`, `BRAND_ID=default`,
   `APP_MODE=bank`, `AUTHN_MODE=seeded|ldap`, `LDAP_*`, `BACKUP_AGE_RECIPIENT=`,
   `REDIS_URL=redis://redis:6379/0`, `DATABASE_URL=...`.
3. `deploy/Caddyfile.template` — placeholders для domain + TLS (Let's Encrypt
   автоматически для internet-facing; банк-internal — внутренний CA через
   `tls /run/secrets/cert /run/secrets/key`).
4. `deploy/systemd/credit-assistant.service`:
   - `ExecStart=/usr/bin/docker compose -f /opt/credit-assistant/docker-compose.prod.yml up`.
   - `ExecStop=/usr/bin/docker compose ... down`.
   - `Restart=on-failure`, `User=root` (Docker requirement).
5. `deploy/systemd/credit-restore-drill.service` + `.timer` (weekly drill).
6. `docker-compose.prod.yml` — production override:
   - `api` service: `image: credit-api:vX.Y.Z` (не build), `env_file: /opt/credit-assistant/.env`.
   - `web` service: `image: credit-web:vX.Y.Z`, expose 3000 (internal only).
   - `caddy` service: `image: caddy:2-alpine`, ports 80/443 host-bound,
     mount Caddyfile + `caddy_data` volume.
   - `postgres`/`redis` без host port-bind (только internal compose-network).
7. `deploy/scripts/load_images.sh` — helper for re-load images on upgrade.

**Verify:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml
config` syntax check.

**Commit:** `feat(deploy): T3.6.2 install.sh + Caddy + systemd + compose.prod`.

---

### T3.6.3 — Release tarball builder (~2 файла)

**Файлы:**
1. `scripts/build_release_tarball.sh`:
   - Build api/web/caddy images с tag `vX.Y.Z` (semver из `pyproject.toml`
     или git tag).
   - `docker save credit-api:vX.Y.Z | gzip > /tmp/release/images/api.tar.gz`.
   - Bundle: `src/`, `scripts/`, `config/`, `deploy/`, миграции Alembic,
     `docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.backup.yml`,
     `README.md`, `LICENSE`.
   - **Exclude** `tests/`, `.git/`, `node_modules/`, `__pycache__/`,
     `.env`, `*.dump*`, `backup-pre-t13.sql`, `smoke-pdfs/`.
   - SHA256 checksum: `sha256sum credit-assistant-vX.Y.Z.tar.gz > .sha256`.
   - Output в `dist/`.
2. `.gitignore` — `dist/` добавить.

**Verify:**
```bash
./scripts/build_release_tarball.sh
ls -lh dist/credit-assistant-*.tar.gz   # ~600MB-1.5GB (3 images compressed)
```

**Commit:** `feat(deploy): T3.6.3 release tarball builder`.

---

### T3.6.4 — ADR-0021 + deploy/README.md "0 → running" (~2 файла)

**Файлы:**
1. `docs/adr/0021-onprem-tarball-deploy.md`:
   - Context: банкам УЗб нет internal registry; zero-internet install;
     `docker save` стандарт.
   - Decision: bundled tarball — api/web/caddy images + scripts + configs +
     install.sh + systemd. `docker compose` orchestrates, systemd boots.
   - Trade-offs: tarball size ~1GB vs registry-pull (быстрее update'ы, но
     требует internet); systemd vs Kubernetes (банк-IT не имеет K8s — overkill).
   - Out of scope: HA / multi-host / rolling upgrade.
2. `deploy/README.md` — "0 → running" walkthrough:
   - **Section 1**: Preconditions (Linux x86_64, Docker 24+, 2 CPU / 4 GB RAM /
     20 GB disk, ports 80/443 free).
   - **Section 2**: Extract + secrets — `tar xzf credit-assistant-vX.Y.Z.tar.gz
     -C /opt/`, edit `/opt/credit-assistant/.env` (PII_ENC_KEYS, JWT_SECRET,
     BRAND_ID, AUTHN_MODE, ...).
   - **Section 3**: Run `install.sh` — что делает по шагам.
   - **Section 4**: Verify — `curl https://localhost/health`, admin user seed,
     первый login.
   - **Section 5**: Upgrade procedure (extract new tarball → `install.sh` again
     → migrations apply через entrypoint).
   - **Section 6**: Troubleshooting (Docker offline / Caddy can't bind 443 /
     migrations fail).
   - **Section 7**: Uninstall (cleanup без data loss + with data loss).

**Commit:** `docs(arch): T3.6.4 ADR-0021 + on-prem deploy README`.

---

### T3.6.5 — Docs sync (~2 файла)

**Файлы:**
1. `CLAUDE.md` — Current Status новая запись T3.6 closed + tick.
2. `docs/pre-demo-roadmap.md` — Tier 3 status section.

**Commit:** `docs(internal): T3.6 closure + Tier 3 progress`.

---

## Verify (full)

После каждого atomic commit:
```bash
PYTHONPATH=src uv run --no-sync python -m ruff check . && \
  uv run --no-sync python -m mypy --strict src/ tests/ && \
  bash -n scripts/*.sh deploy/install.sh
```

Real smoke (требует Docker): tarball build + extract в `/tmp/test-install/`
+ install.sh run + curl health — выполнить **до** банк-tender'а.

## Estimate

- T3.6.1 frontend Dockerfile — 2h
- T3.6.2 deploy artifacts — 4h (самый dense, много файлов)
- T3.6.3 tarball builder — 2h
- T3.6.4 ADR + README — 3h
- T3.6.5 docs — 0.5h

**Total: ~11.5h.**

## Risks / open subtleties

- **Frontend cookies dynamic**: `next.config.ts` с `output: "standalone"`
  должен корректно собрать тот же app, что dev — risk на server actions /
  cookies invariants. Тестируем `npm run build` локально перед коммитом.
- **Caddy внутренний CA**: банк-internal install может не иметь Let's Encrypt
  reachability. Caddyfile template поддерживает оба пути; README объясняет
  выбор.
- **Tarball size**: ~1 GB с 3 images. Доставка через USB-stick / SFTP к банк-сервеу
  предусмотрена. Альтернатива (split-tar для меньших chunks) — backlog если
  банк не сможет принять single-file.
- **Postgres data volume**: первый install создаёт `pgdata` named volume.
  Upgrade — оставляет volume, переустанавливает images. Полная wipe-install —
  manual `docker volume rm` (в README).
- **`install.sh` idempotency**: повторный run на уже-installed системе —
  должен detect existing systemd unit + .env + просто перезапустить compose.
  Не должен затирать `.env`.
- **systemd vs Docker socket access**: systemd unit запускается как root для
  docker.sock access; для bank-IT compliance — позже migrate на rootless
  Docker (post-demo).
- **Multi-tenant brand-tenant**: install.sh принимает один `BRAND_ID`. Для
  нескольких банков на одной машине — separate `/opt/credit-assistant-<bank>/`
  install и offset ports (см. T1.4 multi-tenant playbook).
