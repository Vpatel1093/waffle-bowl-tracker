#!/usr/bin/env bash
set -euo pipefail

APP="${1:-}"
if [ -z "$APP" ]; then
  echo "Usage: $0 <fly-app-name>"
  exit 1
fi

COMMON="$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ ! -f "$COMMON" ]; then
  echo "Missing $COMMON" >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$COMMON"

if ! command -v flyctl >/dev/null 2>&1; then
  echo "flyctl not found in PATH. Install and login first."
  exit 1
fi

# Check if Docker containers are running
if ! docker compose ps | grep -q "waffle_app.*Up"; then
  echo "Docker containers not running. Starting them..."
  docker compose up -d
  sleep 3
fi

echo "Running interactive OAuth setup in Docker container. Follow prompts in browser..."
docker compose exec app python -m app.utils.oauth_setup

# Copy tokens from container to local machine
echo "Copying tokens from Docker container to local machine..."
docker compose exec app cat /root/.yf_token_store/token.json > /tmp/token.json

TOKEN_FILE="/tmp/token.json"
if [ ! -f "$TOKEN_FILE" ]; then
  echo "token.json not found at $TOKEN_FILE"
  exit 1
fi

echo "Pushing tokens from $TOKEN_FILE to Fly app: $APP"
push_fly_secrets "$APP" "$TOKEN_FILE"

echo "✅ Fly secrets updated. Now deploy or restart the app: fly deploy -a $APP"
