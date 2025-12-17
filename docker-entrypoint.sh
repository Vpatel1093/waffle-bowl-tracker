#!/bin/sh
set -e

echo "== entrypoint: initialize yf token store from environment (if provided) =="
TOKEN_DIR="/root/.yf_token_store"
mkdir -p "$TOKEN_DIR"
TOKEN_FILE="$TOKEN_DIR/token.json"
PRIVATE_FILE="$TOKEN_DIR/private.json"

# If we have refresh/access tokens in env, write token.json (YFPY expects this filename)
if [ -n "$YAHOO_REFRESH_TOKEN" ] && [ -n "$YAHOO_CLIENT_ID" ] && [ -n "$YAHOO_CLIENT_SECRET" ]; then
  echo "Writing token.json from environment variables (will overwrite existing file)"
  python - <<'PY' || { echo "ERROR: Failed to write token.json" >&2; exit 1; }
import os, json, time, sys
try:
  d = {
    "access_token": os.environ.get("YAHOO_ACCESS_TOKEN"),
    "refresh_token": os.environ.get("YAHOO_REFRESH_TOKEN"),
    "consumer_key": os.environ.get("YAHOO_CLIENT_ID"),
    "consumer_secret": os.environ.get("YAHOO_CLIENT_SECRET"),
    "guid": None,
    "token_time": int(time.time()),
    "token_type": "bearer"
  }
  with open("/root/.yf_token_store/token.json", "w") as f:
    json.dump(d, f)
    os.chmod("/root/.yf_token_store/token.json", 0o600)
  print("wrote /root/.yf_token_store/token.json with 0600 permissions")
except Exception as e:
  print(f"ERROR: {e}", file=sys.stderr)
  sys.exit(1)
PY
else
  echo "YAHOO_REFRESH_TOKEN or client creds missing; leaving token.json as-is (if present)"
fi

# Always ensure private.json exists (write/overwrite if creds are present)
if [ -n "$YAHOO_CLIENT_ID" ] && [ -n "$YAHOO_CLIENT_SECRET" ]; then
  echo "Writing private.json from environment variables"
  python - <<'PY' || { echo "ERROR: Failed to write private.json" >&2; exit 1; }
import os, json, sys
try:
  d = {
    "consumer_key": os.environ.get("YAHOO_CLIENT_ID"),
    "consumer_secret": os.environ.get("YAHOO_CLIENT_SECRET")
  }
  with open("/root/.yf_token_store/private.json", "w") as f:
    json.dump(d, f)
    os.chmod("/root/.yf_token_store/private.json", 0o600)
  print("wrote /root/.yf_token_store/private.json with 0600 permissions")
except Exception as e:
  print(f"ERROR: {e}", file=sys.stderr)
  sys.exit(1)
PY
else
  echo "YAHOO_CLIENT_ID/YAHOO_CLIENT_SECRET not set; private.json not written"
fi

echo "Entrypoint env preview (YAHOO_CLIENT_ID present?):" [ -n "$YAHOO_CLIENT_ID" ] && echo "yes" || echo "no"

# Exec provided command (Docker passes CMD args to ENTRYPOINT)
echo "Executing command: $@"
exec "$@"
