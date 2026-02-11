# Waffle Bowl Tracker 🧇

A Yahoo Fantasy Football losers bracket tracker where the bottom 6 teams compete to avoid last place. Built with Flask, HTMX, and Tailwind CSS.

## What is the Waffle Bowl?

The Waffle Bowl is a losers bracket where the **worst teams compete in the playoffs**. The ultimate loser earns last place and a reservation at waffle house.

### Bracket Structure (6 Teams)
- **Seeding**: Bottom 6 teams by record (worst = seed 1)
- **The Twist**: Seeds 1-2 (worst two teams) get **BYES** in Round 1
- **Week 1 (Quarterfinals)**: 3v6, 4v5
- **Week 2 (Semifinals)**: QF losers vs bye teams
- **Week 3 (Finals)**: Semifinal losers compete for LAST PLACE 🧇

## Features

- ✅ **No login required** - Public bracket viewing
- ✅ **Live score updates** - 15-second cache for near real-time scores
- ✅ **Mobile-friendly** - Responsive design with Tailwind CSS
- ✅ **Auto-refresh** - HTMX updates bracket every 60 seconds
- ✅ **Team details** - Click any team to see roster and stats

---

## Setup Guide

### Prerequisites
- Python 3.12+
- Yahoo Fantasy Football league
- Redis (for caching)

### 1. Yahoo Developer App Setup

1. Go to [Yahoo Developer Apps](https://developer.yahoo.com/apps/create/)
2. Create a new app:
   - **App Name**: Waffle Bowl
   - **Description**: Yahoo Fantasy Football Waffle Bowl tracker 🧇
   - **Redirect URI**: `https://localhost:8080/auth/callback` (for local dev with Docker)
   - **API Permissions**: Fantasy Sports (Read)
   - **OAuth Client Type**: Confidential Client
3. Save your **Client ID** and **Client Secret**

### 2. Project Setup

```bash
# Clone/download the project
cd waffle-bowl-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Redis (if not already installed)
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
# Windows: Download from https://github.com/microsoftarchive/redis/releases

# Start Redis
redis-server
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials:
# - YAHOO_CLIENT_ID (from Yahoo Developer)
# - YAHOO_CLIENT_SECRET (from Yahoo Developer)
# - LEAGUE_ID (from your Yahoo Fantasy league URL)
```

### 4. Get Yahoo League ID

1. Go to your Yahoo Fantasy Football league
2. Look at the URL: `https://football.fantasysports.yahoo.com/f1/{LEAGUE_ID}`
3. Copy the `LEAGUE_ID` and add it to `.env`

### 5. One-Time OAuth Setup

```bash
# Run the OAuth setup script
python -m app.utils.oauth_setup

# This will:
# 1. Open your browser for Yahoo authorization
# 2. Generate access tokens
# 3. Save tokens to .env file
```

**Important**: You need HTTPS for local OAuth. Use one of these methods:
- **Option A (Recommended)**: Use ngrok
  ```bash
  ngrok http 8080
  # Update YAHOO_REDIRECT_URI in .env to the ngrok HTTPS URL
  ```
- **Option B**: Use Flask's self-signed cert
  ```bash
  flask run --cert=adhoc --port=8080
  ```

### 6. Run the App

```bash
# Make sure Redis is running
redis-server

# Start the Flask app
flask run --cert=adhoc --port=8080

# Or for production mode:
gunicorn wsgi:app -b 0.0.0.0:8080
```

Visit `https://localhost:8080` to see your Waffle Bowl!

**Note:** For the easiest setup, use Docker Compose instead (see Docker section below) - just run `make dev`!

---

## Fly.io Deployment (stateless tokens)

We use a stateless token workflow. The container entrypoint writes YFPY token files from environment secrets at start, so you do not need a persistent token volume for basic deployments.

Recommended flow
1. Ensure you are logged into Fly: `flyctl auth login`
2. Push interactive OAuth tokens to Fly and deploy in one step:
   - From this repo run:
     ```
     make deploy
     ```
     This runs the helper `./scripts/tokens/push-to-fly.sh` to update Fly secrets (interactive browser step may open), then runs `flyctl deploy -a <your-fly-app-name>`.
3. Alternatively, run the helper and deploy separately:
   - `./scripts/tokens/push-to-fly.sh <your-fly-app-name>`
   - `flyctl deploy -a <your-fly-app-name>`

Local development
- To update local tokens (interactive + auto-update .env):
  - `make refresh-tokens`
    - This runs `python -m app.utils.oauth_setup` (opens browser) and writes the resulting
      YAHOO_ACCESS_TOKEN / YAHOO_REFRESH_TOKEN (and client creds when present) into the project's `.env`.
  - After updating tokens restart compose:
    - `make down && make up --build`

Notes about tokens & refresh
- YFPY will use the refresh token + client creds to obtain fresh access tokens when needed; it writes refreshed access tokens to token.json at runtime.
- With the stateless approach, runtime-updated access_tokens are ephemeral (not persisted across redeploys) because we do not mount a persistent token volume. The authoritative credential you must keep in secrets is the refresh token — on each start the entrypoint will re-create token.json from that secret.
- If a refresh token becomes invalid/expired, re-run the interactive oauth setup locally to obtain a new refresh token, then update the Fly secret (using the helper script or manually) and redeploy.

Security
- Keep YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET / YAHOO_REFRESH_TOKEN in a secrets store (Fly secrets, etc.), not in git.
- Rotate secrets if they are accidentally committed.

---

## Year-Over-Year Reusability 🔄

**The app is designed to be used season after season with minimal effort!**

### End of Season (After Playoffs)

**For truly $0 cost in the off-season**, destroy the entire app:

```bash
# Destroy everything (app, machines, volumes)
fly apps destroy waffle-bowl-tracker --yes
```

**Why destroy instead of suspend?**
- Guarantees $0 cost (no compute, no storage)
- Clean slate for next season
- No orphaned resources to manage
- Re-authentication takes <5 minutes with the OAuth script

**Note:** You'll need to re-authenticate with Yahoo next season, but this is simple with `./scripts/tokens/manual-oauth.sh`.

### Start of Next Season

1. **Update your League ID** (if needed)
   - Go to your Yahoo Fantasy league
   - Check the URL for the league ID
   - Update `.env` locally:
     ```bash
     LEAGUE_ID=<new-league-id>
     ```

2. **Deploy to Fly.io**
   ```bash
   fly deploy
   ```

3. **Re-authenticate with Yahoo**
   ```bash
   # Run the manual OAuth script
   ./scripts/tokens/manual-oauth.sh

   # Push tokens to Fly
   ./scripts/tokens/push-to-fly.sh
   ```

4. **Done!** 🧇
   - Your Waffle Bowl is live for the new season
   - Takes ~5 minutes total
   - Fresh deployment with updated config

### Why This Works

- **No database** - All data fetched fresh from Yahoo API
- **Stateless design** - No historical data stored
- **Auto season detection** - App detects current NFL week automatically
- **Simple redeployment** - Fresh deployment each season with updated config
- **Fast OAuth refresh** - Re-authentication takes ~5 minutes with helper scripts
- **Cost effective** - $0 in off-season, minimal compute during season

### Potential Year-Over-Year Issues

| Issue | Solution |
|-------|----------|
| League ID changed | Update `LEAGUE_ID` in `.env`, redeploy |
| Need fresh OAuth tokens | Run `./scripts/tokens/manual-oauth.sh` and `./scripts/tokens/push-to-fly.sh` |
| Yahoo API changes | Update YFPY: `pip install --upgrade yfpy`, redeploy |
| Playoff weeks shifted | App auto-detects weeks, but verify bracket timing in code |

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YAHOO_CLIENT_ID` | Yahoo Developer app Client ID | Required |
| `YAHOO_CLIENT_SECRET` | Yahoo Developer app Client Secret | Required |
| `YAHOO_ACCESS_TOKEN` | OAuth access token (from setup) | Required |
| `YAHOO_REFRESH_TOKEN` | OAuth refresh token (from setup) | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `LEAGUE_ID` | Yahoo Fantasy league ID | Required |
| `WAFFLE_BOWL_TEAMS` | Number of teams in bracket | `6` |
| `CACHE_LIVE_SCORES` | Score cache time (seconds) | `30` |

### Cache Strategy

- **Live scores**: 30 seconds (configurable via `CACHE_LIVE_SCORES`)
- **Standings**: 1 minute
- **Rosters**: 15 minutes

**Rate Limit Math**: With 15s cache:
- 4 requests/minute × 60 minutes = 240 requests/hour
- 240 × 24 = 5,760 requests/day (well under Yahoo's 10,000/day limit)

---

## Development

### Running Tests
```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=app
```

### Clear Redis Cache
```bash
# Connect to Redis
redis-cli

# Clear all cache
FLUSHALL

# Or use the built-in endpoint
curl http://localhost:8080/api/cache/clear
```

### Manual OAuth Token Refresh
If tokens expire, re-run:
```bash
python -m app.utils.oauth_setup
```

---

## Troubleshooting

### "Could not initialize Yahoo API"
- Run `python -m app.utils.oauth_setup`
- Verify `YAHOO_CLIENT_ID` and `YAHOO_CLIENT_SECRET` in `.env`
- Check that `.yf_token_store/oauth2.json` exists in your home directory

### "No bracket data available"
- Verify `LEAGUE_ID` is correct in `.env`
- Check that your league has started (current week > 0)
- Ensure Redis is running: `redis-cli ping` should return `PONG`

### Scores not updating
- Check Redis is running
- Verify `CACHE_LIVE_SCORES` setting in `.env`
- Check browser console for HTMX errors

### HTTPS required for OAuth
- Use ngrok: `ngrok http 8080`
- Or Flask adhoc SSL: `flask run --cert=adhoc`
- Update `YAHOO_REDIRECT_URI` accordingly

---

## Tech Stack

- **Backend**: Flask 3.1.0 (Python web framework)
- **Yahoo API**: YFPY 13.0.0 (Yahoo Fantasy API wrapper)
- **Frontend**: HTMX 2.0.4 (dynamic updates without JavaScript)
- **CSS**: Tailwind CSS (utility-first styling)
- **Caching**: Redis 5.2.0 (Upstash Redis on Fly.io)
- **Deployment**: Fly.io + Docker + Gunicorn
- **Persistent Storage**: Fly.io Volumes (for OAuth token refresh)

---

## Contributing

This is a personal project, but feel free to fork and customize for your league!

---

## License

MIT License - feel free to use and modify!

---

## Credits

- Built with [Claude Code](https://claude.com/claude-code)
- Yahoo Fantasy API via [YFPY](https://github.com/uberfastman/yfpy)

---

**May the odds be ever in your favor... or not. 🧇**

# Waffle Bowl Tracker

## Quick start (Docker)
- Install Docker & Docker Compose.
- Create a `.env` in the project root (see "Environment").
- Foreground (attached): `make dev` — containers run in your terminal, logs stream here, and Ctrl+C stops the services.
- Background (detached): `make up` — containers run in the background. Open a new terminal and run `make logs` to follow logs, and `make down` to stop/remove services.
- The included `docker-compose.yml` runs the app + Redis and passes `.env` into the app via `env_file`.

### Ports & protocol
- The app listens on container port 8080 and the Makefile/compose maps it to host 8080 by default.
- Use http://localhost:8080 unless you explicitly configure TLS inside the container.

### Redis options
- Compose (recommended): `docker compose` will create a `redis` service and the app will use `REDIS_HOST=redis` as configured in compose.
- Host Redis: if you prefer the host machine's Redis, set `REDIS_HOST=host.docker.internal` (macOS/Windows) or use `--add-host=host.docker.internal:host-gateway` on Linux and set `REDIS_HOST` accordingly.

### Environment variables and secrets
- `docker compose` will read `.env` and `env_file` entries; the container will receive the variables set in `.env` automatically when you use these features.
- If container logs show missing values (e.g. empty `client_id` in OAuth URL), ensure `.env` contains the required keys and is passed to the container (via `env_file` or `--env-file`).
- Security: do NOT commit your real `.env` with secrets. Remove it from git history and rotate secrets if already committed.

### Troubleshooting
- "port is already allocated" -> something on the host is already using port 8080. Diagnose with:
  - `docker ps`
  - `sudo lsof -iTCP:8080 -sTCP:LISTEN -n -P` (macOS/Linux)
  - Stop the conflicting process or change host mapping to e.g. `8081:8080` in compose or when running `docker run`.
- Inspect container env:
  - `docker compose exec app env | grep -i YAHOO`
  - `docker compose logs -f` to watch

### OAuth tokens and deployment (stateless — Option B)

We use a stateless token workflow: the container entrypoint writes YFPY token files from environment secrets each time the container starts. This keeps deploys simple and avoids managing a persistent token volume.

How ENTRYPOINT and CMD work
- ENTRYPOINT is the image script (/docker-entrypoint.sh). It initializes token files from env/secrets and then execs the command arguments.
- CMD in the Dockerfile provides default args (our CMD runs gunicorn). Docker runs: /docker-entrypoint.sh <CMD-args>, so the entrypoint does init and then starts the server.

Recommended production flow (Fly)
1. Ensure secrets are set in Fly (client creds + refresh token):
   - flyctl secrets set \
     YAHOO_CLIENT_ID=<id> \
     YAHOO_CLIENT_SECRET=<secret> \
     YAHOO_REFRESH_TOKEN=<refresh-token> \
     -a <appname>
2. Deploy or restart the app:
   - fly deploy -a <appname>  (or fly apps restart <appname>)
   - Or from this repo (convenience): FLY_APP=<appname> make deploy
3. The entrypoint will write /root/.yf_token_store/token.json from the secrets and YFPY will refresh access tokens as needed during runtime.

Local dev (Make)
- Use `.env` for local values and run:
  - make dev     # runs the same image/entrypoint + CMD locally
- After editing `.env` restart:
  - make down && make up --build

Updating/rotating the refresh token
- When you generate a new refresh token (interactive oauth setup):
  1. Run locally: python -m app.utils.oauth_setup (opens browser; get new refresh token)
  2. Update the platform secret (Fly) or `.env` locally:
     - Fly: flyctl secrets set YAHOO_REFRESH_TOKEN=<new-refresh> -a <appname>
     - Local: edit `.env` then restart compose
  3. Redeploy/restart so entrypoint overwrites token.json with the new secret.

Why this works without persisting token.json
- YFPY uses the refresh token + client credentials to obtain fresh access tokens when needed. Those refreshed access tokens are written to token.json at runtime but are ephemeral if you don't mount a volume. On restart the entrypoint re-creates token.json from the authoritative secret (refresh token), and YFPY can refresh again. If the refresh token itself becomes invalid you must re-run the interactive oauth setup and update the secret.

When to use a persistent token volume
- If you want runtime-refreshed access tokens to survive container restarts (avoid re-refreshing on each restart), mount a persistent volume at `/root/.yf_token_store`. This adds operational complexity; for minimal infra choose the stateless approach.

Quick verification
- Inspect token in a running container:
  - docker compose exec app cat /root/.yf_token_store/token.json
- Check logs for successful init and token refresh messages:
  - docker compose logs -f app
