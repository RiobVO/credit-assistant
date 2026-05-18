#!/usr/bin/env bash
# T3.4 — Postgres backup script.
#
# Env contract:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE  — connection.
#   BACKUP_DIR              — destination dir (default /var/backups/credit-assistant).
#   BACKUP_RETENTION_DAYS   — keep dumps modified within last N days (default 7).
#   BACKUP_AGE_RECIPIENT    — optional age public key; задан → output .dump.age.
#
# Output: $BACKUP_DIR/<UTC_TIMESTAMP>.dump[.age].
#
# Exit codes:
#   0   ok
#   10  pg_dump fail (включая authentication)
#   11  age encryption fail
#   12  retention cleanup fail
#
# Logging — stderr в формате "[ISO_TS] [level] message" (systemd journal compat).

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/credit-assistant}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_AGE_RECIPIENT="${BACKUP_AGE_RECIPIENT:-}"

log() {
  local level="$1"
  shift
  printf '[%s] [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" >&2
}

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    log error "Required binary not found: $bin"
    return 1
  fi
}

require_bin pg_dump

mkdir -p "$BACKUP_DIR"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$BACKUP_DIR/.${ts}.dump.tmp"
final="$BACKUP_DIR/${ts}.dump"

log info "Starting pg_dump database=${PGDATABASE} host=${PGHOST}"

if ! pg_dump \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl \
  --file="$tmp"; then
  log error "pg_dump failed"
  rm -f "$tmp"
  exit 10
fi

if [[ -n "$BACKUP_AGE_RECIPIENT" ]]; then
  require_bin age
  log info "Encrypting dump with age recipient"
  if ! age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" \
    --output "${final}.age" "$tmp"; then
    log error "age encryption failed"
    rm -f "$tmp"
    exit 11
  fi
  rm -f "$tmp"
  final="${final}.age"
else
  mv "$tmp" "$final"
fi

size="$(wc -c <"$final")"
log info "Backup written: $final (${size} bytes)"

# Retention: удалить файлы старше N дней. Грепаем оба расширения.
if ! find "$BACKUP_DIR" \
  -maxdepth 1 \
  -type f \
  \( -name '*.dump' -o -name '*.dump.age' \) \
  -mtime "+${BACKUP_RETENTION_DAYS}" \
  -delete; then
  log error "retention cleanup failed"
  exit 12
fi

log info "Done"
