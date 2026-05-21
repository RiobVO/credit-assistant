#!/usr/bin/env bash
# T3.6 — Credit Assistant on-prem installer.
#
# Использование:
#   1. tar xzf credit-assistant-vX.Y.Z.tar.gz -C /opt/
#   2. cd /opt/credit-assistant
#   3. cp deploy/.env.example .env  # отредактировать секреты
#   4. sudo ./deploy/install.sh
#
# Скрипт идемпотентен — повторный run переустановит systemd unit и
# перезапустит compose, но НЕ затрёт ``.env`` и pgdata volume.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/credit-assistant}"
ENV_FILE="${ENV_FILE:-$INSTALL_DIR/.env}"

log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" >&2
}

require_root() {
  if [[ "$EUID" -ne 0 ]]; then
    log error "install.sh требует root (docker.sock + /etc/systemd write)."
    exit 1
  fi
}

require_bin() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log error "Required binary not found: $1"
    exit 1
  fi
}

# ─── Preflight ───────────────────────────────────────────────────────────────

require_root
require_bin docker
require_bin tar
require_bin gzip
require_bin systemctl

if ! docker compose version >/dev/null 2>&1; then
  log error "'docker compose' plugin не установлен. Apt: docker-compose-plugin."
  exit 1
fi

if [[ ! -d "$INSTALL_DIR" ]]; then
  log error "Install dir $INSTALL_DIR не существует. Extract tarball: tar xzf ... -C /opt/"
  exit 1
fi

cd "$INSTALL_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  log error ".env не найден: $ENV_FILE"
  log error "  Скопируйте: cp deploy/.env.example .env  и отредактируйте."
  exit 1
fi

# ─── .env validation ─────────────────────────────────────────────────────────

# shellcheck disable=SC1090
set -a
. "$ENV_FILE"
set +a

validate_env() {
  local missing=()

  [[ -z "${JWT_SECRET:-}" || "${JWT_SECRET}" == *"CHANGE_ME"* ]] && missing+=("JWT_SECRET")
  if [[ -n "${JWT_SECRET:-}" && ${#JWT_SECRET} -lt 32 ]]; then
    log error "JWT_SECRET должен быть ≥32 chars (текущая длина ${#JWT_SECRET})."
    exit 2
  fi

  [[ -z "${POSTGRES_PASSWORD:-}" || "${POSTGRES_PASSWORD}" == *"CHANGE_ME"* ]] && missing+=("POSTGRES_PASSWORD")

  # PII_ENC_KEYS обязателен в staging/prod (T1.3 / ADR-0017).
  if [[ "${APP_ENV:-prod}" =~ ^(staging|prod)$ ]] && [[ -z "${PII_ENC_KEYS:-}" ]]; then
    missing+=("PII_ENC_KEYS")
  fi

  [[ -z "${BRAND_ID:-}" ]] && missing+=("BRAND_ID")

  if [[ "${AUTHN_MODE:-seeded}" == "ldap" ]]; then
    for v in LDAP_URI LDAP_BASE_DN LDAP_BIND_DN LDAP_BIND_PASSWORD \
             LDAP_ROLE_ANALYST_GROUP LDAP_ROLE_SENIOR_ANALYST_GROUP; do
      [[ -z "${!v:-}" ]] && missing+=("$v")
    done
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    log error "Missing required .env values: ${missing[*]}"
    log error "Заполните их в $ENV_FILE и запустите install.sh снова."
    exit 2
  fi

  # BRAND_ID должен резолвиться в config/brands/<id>.json.
  if [[ ! -f "$INSTALL_DIR/config/brands/${BRAND_ID}.json" ]]; then
    log error "BRAND_ID='${BRAND_ID}' не резолвится в config/brands/${BRAND_ID}.json"
    exit 2
  fi
}

log info "Validating .env"
validate_env
log info ".env OK"

# ─── Load Docker images from tarball ─────────────────────────────────────────

IMAGES_DIR="$INSTALL_DIR/images"
if [[ -d "$IMAGES_DIR" ]]; then
  log info "Loading Docker images from $IMAGES_DIR"
  for archive in "$IMAGES_DIR"/*.tar.gz; do
    [[ -f "$archive" ]] || continue
    log info "  loading $(basename "$archive")"
    gunzip -c "$archive" | docker load
  done
else
  log info "No bundled images dir — assuming images already loaded или будут built'нуты compose'ом."
fi

# ─── Install systemd units ───────────────────────────────────────────────────

log info "Installing systemd units"
install -m 0644 "$INSTALL_DIR/deploy/systemd/credit-assistant.service" /etc/systemd/system/
install -m 0644 "$INSTALL_DIR/deploy/systemd/credit-restore-drill.service" /etc/systemd/system/
install -m 0644 "$INSTALL_DIR/deploy/systemd/credit-restore-drill.timer" /etc/systemd/system/
systemctl daemon-reload

# ─── Start stack ─────────────────────────────────────────────────────────────

log info "Enabling + starting credit-assistant.service"
systemctl enable --now credit-assistant.service

log info "Enabling weekly restore drill timer"
systemctl enable --now credit-restore-drill.timer

# ─── Verify ──────────────────────────────────────────────────────────────────

log info "Waiting for API health (max 90s)"
for i in $(seq 1 18); do
  if curl -fsS "http://127.0.0.1:80/health" >/dev/null 2>&1; then
    log info "API healthy after ${i}*5=$((i*5))s"
    break
  fi
  if [[ "$i" -eq 18 ]]; then
    log warn "API не отвечает на /health после 90s. Проверьте: journalctl -u credit-assistant -n 100"
  fi
  sleep 5
done

cat <<EOF

══════════════════════════════════════════════════════════════════════
  Credit Assistant установлен.

  URL:           https://${CADDY_DOMAIN:-<set CADDY_DOMAIN in .env>}/
  Logs:          journalctl -u credit-assistant -f
  Backup logs:   journalctl -u credit-restore-drill -f
  Manual stop:   sudo systemctl stop credit-assistant
  Manual start:  sudo systemctl start credit-assistant

  Следующий шаг — seed первого аналитика:
    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api \\
      bash -c "cd /app/src && uv run --no-sync python -m \\
      interfaces.cli.seed_analysts --email admin@bank.uz \\
      --password CHANGE_ME --full-name 'Admin Analyst'"

  Опционально — seed 5 demo dossiers для pilot walkthrough
  (BR-2026-0030/0040/0042/0046/0047, см. docs/demo/scenarios.md):
    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api \\
      bash -c "cd /app/src && uv run --no-sync python -m \\
      scripts.seed_demo_borrowers --commit"
  Скрипт идемпотентен — повторный запуск skip'ает уже существующие case_id.

  Документация: deploy/README.md
══════════════════════════════════════════════════════════════════════
EOF
