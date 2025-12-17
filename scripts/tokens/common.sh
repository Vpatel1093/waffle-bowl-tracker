#!/usr/bin/env bash
# Common helpers for token management scripts.
set -euo pipefail

TOKEN_FILE_DEFAULT="$HOME/.yf_token_store/token.json"

# read_tokens [token_file]
# Exports: ACCESS_TOKEN REFRESH_TOKEN CLIENT_ID CLIENT_SECRET
read_tokens() {
	_token_file="${1:-$TOKEN_FILE_DEFAULT}"
	if [ ! -f "$_token_file" ]; then
		echo "token.json not found at $_token_file" >&2
		return 1
	fi

	read ACCESS_TOKEN REFRESH_TOKEN CLIENT_ID CLIENT_SECRET <<-EOF
	$(
		python - "$_token_file" <<'PY'
import sys, json
p = sys.argv[1]
d = json.load(open(p))
print(d.get("access_token",""))
print(d.get("refresh_token",""))
print(d.get("consumer_key",""))
print(d.get("consumer_secret",""))
PY
	)
	EOF

	export ACCESS_TOKEN REFRESH_TOKEN CLIENT_ID CLIENT_SECRET
	return 0
}

# update_env_file <env_file> [token_file]
update_env_file() {
	_env_file="${1:?env file required}"
	_token_file="${2:-$TOKEN_FILE_DEFAULT}"

	read_tokens "$_token_file" || return 1

	python - "$_token_file" "$_env_file" <<'PY'
import sys, json, re
token_path = sys.argv[1]
env_path = sys.argv[2]

with open(token_path) as f:
    data = json.load(f)

updates = {
    "YAHOO_ACCESS_TOKEN": data.get("access_token", "") or "",
    "YAHOO_REFRESH_TOKEN": data.get("refresh_token", "") or "",
    "YAHOO_CLIENT_ID": data.get("consumer_key", "") or None,
    "YAHOO_CLIENT_SECRET": data.get("consumer_secret", "") or None,
}

lines = []
try:
    with open(env_path, "r") as f:
        lines = f.read().splitlines()
except FileNotFoundError:
    lines = []

env = {}
for i,l in enumerate(lines):
    m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', l)
    if m:
        k = m.group(1)
        v = m.group(2)
        env[k] = (i, v)

for k, val in updates.items():
    if val is None:
        continue
    if k.startswith("YAHOO_CLIENT") and val == "":
        continue
    if k in env:
        idx, _ = env[k]
        lines[idx] = f'{k}={val}'
    else:
        lines.append(f'{k}={val}')

with open(env_path, "w") as f:
    f.write("\n".join(lines) + ("\n" if lines and not lines[-1].endswith("\n") else ""))
print(f"Wrote updates to {env_path}")
PY

	echo "Updated $_env_file"
	return 0
}

# push_fly_secrets <fly_app> [token_file]
push_fly_secrets() {
	_app="${1:?Fly app name required}"
	_token_file="${2:-$TOKEN_FILE_DEFAULT}"

	read_tokens "$_token_file" || return 1

	flyctl secrets set \
		YAHOO_CLIENT_ID="$CLIENT_ID" \
		YAHOO_CLIENT_SECRET="$CLIENT_SECRET" \
		YAHOO_ACCESS_TOKEN="$ACCESS_TOKEN" \
		YAHOO_REFRESH_TOKEN="$REFRESH_TOKEN" \
		-a "$_app"
	return $?
}
