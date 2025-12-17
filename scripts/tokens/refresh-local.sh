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

echo "Running interactive OAuth setup. Follow prompts in browser..."

# Activate venv if it exists
if [ -f "$REPO_ROOT/venv/bin/activate" ]; then
  echo "Activating virtual environment..."
  source "$REPO_ROOT/venv/bin/activate"
fi

python -m app.utils.oauth_setup

if [ ! -f "$TOKEN_FILE" ]; then
  echo "token.json not found at $TOKEN_FILE"
  exit 1
fi

echo "Updating $ENV_FILE with values from $TOKEN_FILE"
update_env_file "$ENV_FILE" "$TOKEN_FILE"

echo "✅ .env updated. Restart your local compose / dev server:"
echo "   make down && make up --build"
