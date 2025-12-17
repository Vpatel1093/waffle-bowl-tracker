#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "[DEPLOY] Waffle Bowl Tracker to Fly.io"
echo "=================================================="
echo ""

# Step 1: Detect Fly app name
echo "[1/3] Detecting Fly app name..."
if [ -n "${FLY_APP:-}" ]; then
    echo "  [OK] Using FLY_APP from environment: $FLY_APP"
else
    if [ -f fly.toml ]; then
        FLY_APP=$(grep -E "^app[[:space:]]*=" fly.toml | sed -E "s/app[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/" | head -n1)
        if [ -n "$FLY_APP" ]; then
            echo "  [OK] Detected from fly.toml: $FLY_APP"
        else
            echo "  [ERROR] Could not parse app name from fly.toml"
            echo "  Please set FLY_APP env var or fix fly.toml"
            exit 1
        fi
    else
        echo "  [ERROR] fly.toml not found and FLY_APP not set"
        echo "  Usage: FLY_APP=<app-name> $0"
        exit 1
    fi
fi

echo ""

# Step 2: Push secrets to Fly
echo "[2/3] Pushing secrets to Fly..."
if [ ! -f .env ]; then
    echo "  [ERROR] .env file not found"
    exit 1
fi

echo "  -> Reading credentials from .env"
echo "  -> Updating Fly secrets for app: $FLY_APP"

flyctl secrets set --app "$FLY_APP" \
    YAHOO_CLIENT_ID="$(grep YAHOO_CLIENT_ID .env | cut -d= -f2-)" \
    YAHOO_CLIENT_SECRET="$(grep YAHOO_CLIENT_SECRET .env | cut -d= -f2-)" \
    YAHOO_ACCESS_TOKEN="$(grep YAHOO_ACCESS_TOKEN .env | cut -d= -f2-)" \
    YAHOO_REFRESH_TOKEN="$(grep YAHOO_REFRESH_TOKEN .env | cut -d= -f2-)" \
    LEAGUE_ID="$(grep LEAGUE_ID .env | cut -d= -f2-)"

echo "  [OK] Secrets updated successfully"
echo ""

# Step 3: Deploy application
echo "[3/3] Deploying application..."
echo "  -> Building and deploying to Fly app: $FLY_APP"

flyctl deploy -a "$FLY_APP"

echo ""
echo "[SUCCESS] Deployment complete!"
echo "[INFO] Your app should be live at: https://$FLY_APP.fly.dev"
