#!/usr/bin/env bash
# T3.6 — Release tarball builder.
#
# Собирает credit-assistant-vX.Y.Z.tar.gz с:
#   - Docker images (api / web / caddy / postgres / redis) — для zero-internet install.
#   - scripts/ config/ deploy/ migrations
#   - docker-compose*.yml + Dockerfile (для rebuild при необходимости).
#   - .env.example + README
#   - SHA256 checksum (.sha256 рядом с tarball'ом).
#
# Использование:
#   ./scripts/build_release_tarball.sh                # vX.Y.Z из pyproject.toml
#   RELEASE_VERSION=v0.2.0 ./scripts/build_release_tarball.sh
#
# Output: dist/credit-assistant-vX.Y.Z.tar.gz (+ .sha256).
#
# Approximate size: ~600 MB - 1.5 GB (3-5 images compressed).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" >&2
}

# Version: из env override или из pyproject.toml.
if [[ -z "${RELEASE_VERSION:-}" ]]; then
  RELEASE_VERSION="v$(grep -E '^version' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"
fi
log info "Release version: $RELEASE_VERSION"

DIST_DIR="$REPO_ROOT/dist"
STAGING="$DIST_DIR/staging-${RELEASE_VERSION}"
TARBALL="$DIST_DIR/credit-assistant-${RELEASE_VERSION}.tar.gz"

rm -rf "$STAGING"
mkdir -p "$STAGING/images"

# ─── Build & save Docker images ─────────────────────────────────────────────

log info "Building api image"
docker build -t "credit-api:${RELEASE_VERSION}" -f Dockerfile .

log info "Building web image"
docker build -t "credit-web:${RELEASE_VERSION}" -f web/Dockerfile web/

log info "Pulling third-party images (caddy / postgres / redis)"
docker pull caddy:2-alpine
docker pull postgres:16-alpine
docker pull redis:7-alpine

log info "Saving images → images/*.tar.gz"
docker save "credit-api:${RELEASE_VERSION}" | gzip -9 > "$STAGING/images/credit-api.tar.gz"
docker save "credit-web:${RELEASE_VERSION}" | gzip -9 > "$STAGING/images/credit-web.tar.gz"
docker save caddy:2-alpine | gzip -9 > "$STAGING/images/caddy.tar.gz"
docker save postgres:16-alpine | gzip -9 > "$STAGING/images/postgres.tar.gz"
docker save redis:7-alpine | gzip -9 > "$STAGING/images/redis.tar.gz"

# ─── Bundle source + configs ────────────────────────────────────────────────

log info "Bundling source / scripts / configs / deploy"

bundle() {
  local src="$1"
  local dst="$STAGING/$2"
  if [[ -d "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  elif [[ -f "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  fi
}

bundle src                              src
bundle scripts                          scripts
bundle config                           config
bundle deploy                           deploy
bundle docker                           docker
bundle web/Dockerfile                   web/Dockerfile
bundle web/.dockerignore                web/.dockerignore
bundle Dockerfile                       Dockerfile
bundle docker-compose.yml               docker-compose.yml
bundle docker-compose.prod.yml          docker-compose.prod.yml
bundle docker-compose.backup.yml        docker-compose.backup.yml
bundle pyproject.toml                   pyproject.toml
bundle uv.lock                          uv.lock
bundle alembic.ini                      alembic.ini
bundle README.md                        README.md
bundle docs/operations                  docs/operations
bundle docs/adr                         docs/adr

# Не включаем: tests/ web/ (только Dockerfile), .git/, dist/, node_modules/,
# .env, *.dump, backup-pre-t13.sql, smoke-pdfs/, photos/.

# ─── Create tarball ─────────────────────────────────────────────────────────

log info "Creating $TARBALL"
tar -C "$DIST_DIR" -czf "$TARBALL" "staging-${RELEASE_VERSION}" \
  --transform "s/^staging-${RELEASE_VERSION}/credit-assistant/"

# ─── Checksum + cleanup ─────────────────────────────────────────────────────

log info "Computing SHA256"
( cd "$DIST_DIR" && sha256sum "$(basename "$TARBALL")" > "${TARBALL}.sha256" )

rm -rf "$STAGING"

size="$(du -h "$TARBALL" | cut -f1)"
log info "Done: $TARBALL ($size)"
log info "SHA256: $(cat "${TARBALL}.sha256")"
log info ""
log info "Install steps:"
log info "  1. scp $TARBALL bank-host:/tmp/"
log info "  2. ssh bank-host"
log info "  3. sudo tar xzf /tmp/$(basename "$TARBALL") -C /opt/"
log info "  4. cd /opt/credit-assistant"
log info "  5. cp deploy/.env.example .env  # отредактировать секреты"
log info "  6. sudo ./deploy/install.sh"
