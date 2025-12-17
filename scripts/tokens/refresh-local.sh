#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOKEN_FILE="$HOME/.yf_token_store/token.json"
ENV_FILE="$REPO_ROOT/.env"

COMMON="$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ ! -f "$COMMON" ]; then
  echo "Missing $COMMON" >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$COMMON"

echo "Running interactive OAuth setup in Docker container. Follow prompts in browser..."

# Check if Docker containers are running
if ! docker compose ps | grep -q "waffle_app.*Up"; then
  echo "Docker containers not running. Starting them..."
  docker compose up -d
  sleep 3
fi

# Run OAuth setup in Docker container
docker compose exec app python -m app.utils.oauth_setup

# Copy tokens from container to local machine
echo "Copying tokens from Docker container to local machine..."
docker compose exec app cat /root/.yf_token_store/token.json > "$TOKEN_FILE"

if [ ! -f "$TOKEN_FILE" ]; then
  echo "token.json not found at $TOKEN_FILE"
  exit 1
fi

echo "Updating $ENV_FILE with values from $TOKEN_FILE"
update_env_file "$ENV_FILE" "$TOKEN_FILE"

echo "✅ .env updated. Restart your local compose / dev server:"
echo "   make down && make up --build"
