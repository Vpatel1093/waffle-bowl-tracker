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

echo "Running interactive OAuth setup. Follow prompts in browser..."
python -m app.utils.oauth_setup

TOKEN_FILE="$HOME/.yf_token_store/token.json"
if [ ! -f "$TOKEN_FILE" ]; then
  echo "token.json not found at $TOKEN_FILE"
  exit 1
fi

echo "Pushing tokens from $TOKEN_FILE to Fly app: $APP"
push_fly_secrets "$APP" "$TOKEN_FILE"

echo "✅ Fly secrets updated. Now deploy or restart the app: fly deploy -a $APP"
