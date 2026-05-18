#!/usr/bin/env bash
# T3.4 — Restore drill: pg_restore latest dump в temp DB, сравнение row counts.
#
# Env contract:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE — source connection.
#   BACKUP_DIR        — directory с *.dump или *.dump.age (default
#                       /var/backups/credit-assistant).
#   AGE_IDENTITY      — путь к age identity file (для .dump.age, иначе error).
#   DRILL_ROW_DIFF_PCT — допустимое расхождение row counts (default 5).
#
# Алгоритм:
#   1. Выбираем newest mtime *.dump или *.dump.age в BACKUP_DIR.
#   2. (Если .age) age decrypt → temp .dump.
#   3. createdb <PGDATABASE>_drill_<ts>.
#   4. pg_restore -d temp -j 4 --no-owner --no-acl <dump>.
#   5. Row counts на обоих БД через pg_stat_user_tables → diff.
#   6. PASS если max diff < DRILL_ROW_DIFF_PCT.
#   7. Drop temp DB (всегда, через trap).
#
# Exit codes:
#   0   PASS
#   20  pg_restore fail
#   21  row-count diff > threshold
#   22  cleanup fail
#   23  no backup file found
#   24  age decrypt fail
#
# Stderr logging — формат "[ISO_TS] [level] message".

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/credit-assistant}"
DRILL_ROW_DIFF_PCT="${DRILL_ROW_DIFF_PCT:-5}"

log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" >&2
}

require_bin() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log error "Required binary not found: $1"
    return 1
  fi
}

require_bin pg_restore
require_bin psql

if [[ ! -d "$BACKUP_DIR" ]]; then
  log error "BACKUP_DIR does not exist: $BACKUP_DIR"
  exit 23
fi

latest="$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name '*.dump' -o -name '*.dump.age' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | awk 'NR==1 {print $2}')"
if [[ -z "$latest" ]]; then
  log error "No backup files in $BACKUP_DIR"
  exit 23
fi

log info "Latest backup: $latest"

work_dump="$latest"
tmpfile=""
if [[ "$latest" == *.age ]]; then
  require_bin age
  if [[ -z "${AGE_IDENTITY:-}" ]]; then
    log error "AGE_IDENTITY required for *.dump.age"
    exit 24
  fi
  tmpfile="$(mktemp --suffix=.dump)"
  if ! age --decrypt --identity "$AGE_IDENTITY" --output "$tmpfile" "$latest"; then
    rm -f "$tmpfile"
    log error "age decrypt failed"
    exit 24
  fi
  work_dump="$tmpfile"
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
temp_db="${PGDATABASE}_drill_${ts}"

cleanup() {
  local code=$?
  if [[ -n "$tmpfile" && -f "$tmpfile" ]]; then
    rm -f "$tmpfile"
  fi
  # PGDATABASE=postgres для maintenance-команд (нельзя drop'нуть current).
  if ! PGDATABASE=postgres psql -v ON_ERROR_STOP=1 -q -c "DROP DATABASE IF EXISTS \"$temp_db\";" >/dev/null 2>&1; then
    log warn "Failed to drop temp DB $temp_db (manual cleanup needed)"
    [[ $code -eq 0 ]] && exit 22
  fi
  exit "$code"
}
trap cleanup EXIT

log info "Creating temp DB: $temp_db"
PGDATABASE=postgres psql -v ON_ERROR_STOP=1 -q -c "CREATE DATABASE \"$temp_db\";" >/dev/null

log info "Restoring into $temp_db"
if ! PGDATABASE="$temp_db" pg_restore --no-owner --no-acl --jobs=4 -d "$temp_db" "$work_dump" 2>/tmp/restore_err.$$; then
  # pg_restore часто пишет non-fatal warnings на stderr но возвращает 0; если
  # вернул non-zero — фатально.
  log error "pg_restore failed: $(cat /tmp/restore_err.$$ 2>/dev/null || true)"
  rm -f /tmp/restore_err.$$
  exit 20
fi
rm -f /tmp/restore_err.$$

# Row counts: используем COUNT(*) per table (точнее, чем n_live_tup в
# pg_stat_user_tables, который обновляется ANALYZE'ом и может врать).
count_rows() {
  local db="$1"
  PGDATABASE="$db" psql -At -F'|' <<'SQL'
SELECT schemaname || '.' || tablename AS qname,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I',
                                  schemaname, tablename),
                          true, true, '')))[1]::text::bigint AS rows
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog','information_schema')
ORDER BY 1;
SQL
}

src_counts="$(count_rows "$PGDATABASE")"
dst_counts="$(count_rows "$temp_db")"

# Сравниваем построчно. Допускаем расхождение в DRILL_ROW_DIFF_PCT% per table.
max_diff_pct=0
diff_table=""
while IFS='|' read -r qname src_n; do
  dst_n="$(awk -F'|' -v k="$qname" '$1==k {print $2}' <<<"$dst_counts")"
  dst_n="${dst_n:-0}"
  if [[ "$src_n" -eq 0 && "$dst_n" -eq 0 ]]; then
    continue
  fi
  base="$src_n"
  [[ "$base" -eq 0 ]] && base="$dst_n"
  diff="$((src_n - dst_n))"
  diff="${diff#-}"
  pct="$(( diff * 100 / base ))"
  if [[ "$pct" -gt "$max_diff_pct" ]]; then
    max_diff_pct="$pct"
    diff_table="$qname (src=$src_n dst=$dst_n)"
  fi
done <<<"$src_counts"

if [[ "$max_diff_pct" -gt "$DRILL_ROW_DIFF_PCT" ]]; then
  log error "Row count diff $max_diff_pct% exceeds threshold $DRILL_ROW_DIFF_PCT%: $diff_table"
  exit 21
fi

log info "PASS — max row diff $max_diff_pct% (threshold $DRILL_ROW_DIFF_PCT%)"
exit 0
