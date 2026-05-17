# ADR-0021 — On-prem deploy via bundled tarball

* Status: accepted
* Date: 2026-05-18
* Tier: T3.6 (operational readiness)

## Context

Бизнес-цель — поставлять Credit Assistant в mid-tier банки УЗб
(Hamkorbank, SQB, Trastbank, Anor, Asia Alliance, Bereke, Davr, Halk,
Mikrokreditbank). Эти банки:

* Не имеют internal Docker registry mirror (Harbor / Nexus / Artifactory).
* Не имеют Kubernetes — bank-IT привычен к bare-metal / systemd.
* Часто требуют **zero-internet install** (production хост в изолированной сети).
* Не приемлют SaaS-only зависимости (PROJECT_BRIEF Sec 11).

Регуляторные ожидания (ЦБ РУз / Базель III):

* Audit-trail на установку (кто, когда, какая версия).
* Восстанавливаемость из артефакта (single source for full re-deploy).
* Reproducibility — та же tarball должна давать ту же установку через год.

Альтернативы рассмотрены:

1. **Registry-pull (Harbor / Quay)** — отвергнут: банки не имеют registry.
2. **Ansible playbook** — overengineered для single-host install, добавляет
   Python+Ansible dependency на bank-side.
3. **Kubernetes Helm chart** — банкам нет K8s; даже если поставим — отвлекает
   от продукта на инфра-stack.
4. **Direct apt repo (debian packaging)** — не подходит для multi-language
   stack (Python + Node + Postgres images).

## Decision

**Доставка через bundled tarball** `credit-assistant-vX.Y.Z.tar.gz` с:

* Docker images (api / web / caddy / postgres:16-alpine / redis:7-alpine) —
  `docker save | gzip -9` для каждого, складываются в `images/`.
* Source code (`src/`), scripts (backup + restore drill + install),
  configs (`config/brands/`, `config/rules/`, `config/pdf-i18n/`),
  Alembic migrations.
* `deploy/` — `.env.example`, `Caddyfile.template`, `install.sh`, systemd units
  (`credit-assistant.service`, `credit-restore-drill.service` + `.timer`).
* `docker-compose.yml` + `docker-compose.prod.yml` + `docker-compose.backup.yml`.
* SHA256 checksum рядом для verification.

**Orchestration**: `docker compose` для container lifecycle, systemd-unit
для boot-time start и restart-on-failure. `install.sh` — bash, требует
`docker`+`docker compose plugin`+`tar`+`gzip` preinstalled.

**Tarball size**: ~600 MB – 1.5 GB (5 images compressed). Доставка через
USB-stick / SFTP / банк-internal artifact repository.

## Consequences

### Positive

* Zero-internet install: всё нужное в одном файле.
* Reproducible: tarball + .sha256 = single source of truth для версии.
* Простой rollback: prev-version tarball → re-extract + `install.sh`.
* Backup-friendly: `pgdata` volume сохраняется, upgrade переставляет только images.
* Bank-IT-friendly: `journalctl -u credit-assistant -f` для troubleshooting,
  systemd для start/stop/enable — стандартный набор.

### Negative

* Tarball size — 600 MB – 1.5 GB. Update'ы тяжёлые. Mitigation: incremental
  upgrade tarballs (только diff images) — backlog post-demo.
* Manual upgrade workflow — нет автоматического rolling update. Окей для
  daily-traffic банк-internal tool; HA / blue-green — post-demo.
* systemd-Docker socket access — `install.sh` ставит unit с `User=root`.
  Bank compliance может потребовать rootless Docker — post-demo migration.
* Caddy bundled — банк-IT не может подменить reverse-proxy без edit'а
  override-compose. Mitigation: `caddy` service в `docker-compose.prod.yml`
  легко выключается (для случая, когда банк уже имеет nginx/F5).

### Neutral

* Multi-tenant (несколько банков на одной машине) — separate install в
  `/opt/credit-assistant-<bank>/` с offset портами (T1.4 multi-tenant
  playbook). Tarball одна для всех — переменные через `.env`.

## Implementation

См.:

* `scripts/build_release_tarball.sh` — builder.
* `deploy/install.sh` — installer.
* `deploy/README.md` — "0 → running" walkthrough.
* `docs/operations/db-backup.md` — backup-runbook (T3.4).

## Out of scope (future ADRs)

* Multi-host / HA deployment.
* Rolling upgrade с zero-downtime.
* Rootless Docker / Podman.
* Air-gapped Helm-chart (если когда-то банк перейдёт на K8s).
