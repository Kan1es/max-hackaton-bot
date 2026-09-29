#!/usr/bin/env bash
# Ship the project to a VPS and (re)start the production stack.
#
#   ./deploy/deploy.sh root@203.0.113.10
#
# The first run installs Docker on the server. The server needs its own .env
# (copied from yours on the first run); later runs never overwrite it.
set -euo pipefail

TARGET="${1:?usage: deploy/deploy.sh user@host}"
REMOTE_DIR="${REMOTE_DIR:-/opt/max-hackaton}"
cd "$(dirname "$0")/.."

ssh "$TARGET" "command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh"
ssh "$TARGET" "mkdir -p $REMOTE_DIR"

# deploy/ru_tunnel_key (gitignored) travels with the rest, permissions
# included (-a). --inplace keeps inodes, so the bind-mounted Caddyfile inside the running
# container sees the new content (a replaced file would stay stale there).
rsync -az --delete --inplace \
  --exclude .git --exclude .venv --exclude '__pycache__' --exclude .pytest_cache \
  --exclude miniapp/node_modules --exclude miniapp/dist \
  --exclude '.env' --exclude '.env.*' --exclude docker-compose.override.yml \
  ./ "$TARGET:$REMOTE_DIR/"

if ! ssh "$TARGET" "test -f $REMOTE_DIR/.env"; then
  echo "No .env on the server yet — uploading deploy/.env.production"
  scp deploy/.env.production "$TARGET:$REMOTE_DIR/.env"
fi

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
ssh "$TARGET" "cd $REMOTE_DIR && $COMPOSE up -d --build --remove-orphans \
  && $COMPOSE exec -T caddy caddy reload --config /etc/caddy/Caddyfile \
  && docker image prune -f >/dev/null && $COMPOSE ps"
