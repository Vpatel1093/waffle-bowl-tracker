# Waffle Bowl Tracker 🧇

A Yahoo Fantasy Football losers bracket tracker where the bottom 6 teams compete to avoid last place. Built with Flask, HTMX, and Tailwind CSS.

## What is the Waffle Bowl?

The Waffle Bowl is a losers bracket where the **worst teams compete in the playoffs**. The twist? **You want to LOSE**. The ultimate loser earns last place.

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
   - **Redirect URI**: `https://localhost:5000/auth/callback` (for local dev)
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
  ngrok http 5000
  # Update YAHOO_REDIRECT_URI in .env to the ngrok HTTPS URL
  ```
- **Option B**: Use Flask's self-signed cert
  ```bash
  flask run --cert=adhoc
  ```

### 6. Run the App

```bash
# Make sure Redis is running
redis-server

# Start the Flask app
flask run --cert=adhoc

# Or for production mode:
gunicorn wsgi:app
```

Visit `https://localhost:5000` to see your Waffle Bowl!

---

## Fly.io Deployment

### Initial Deployment

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Waffle Bowl tracker"
   git branch -M main
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Install Fly.io CLI**
   ```bash
   # macOS
   brew install flyctl

   # Or use install script
   curl -L https://fly.io/install.sh | sh
   ```

3. **Login to Fly.io**
   ```bash
   flyctl auth login
   ```

4. **Launch App (via CLI or Web UI)**

   **Option A: Using CLI**
   ```bash
   # Navigate to project
   cd waffle-bowl-tracker

   # Launch (will use existing fly.toml)
   flyctl launch --no-deploy

   # When prompted:
   # - Choose app name (e.g., "wafflebowl")
   # - Select region (e.g., "iad" - US East)
   # - PostgreSQL: No
   # - Redis: Yes (Upstash Redis)
   ```

   **Option B: Using Web UI**
   - Go to [fly.io/dashboard](https://fly.io/dashboard)
   - Connect your GitHub repository
   - Follow the prompts

5. **Create Persistent Volume for Token Storage**

   **Why?** Yahoo OAuth tokens refresh automatically, but need persistent storage to survive container restarts.

   **Via CLI:**
   ```bash
   flyctl volumes create yahoo_tokens --size 1 --region iad
   ```

   **Via Web UI:**
   - Go to your app → **Volumes**
   - Click **Create Volume**
   - Name: `yahoo_tokens`
   - Size: `1GB`
   - Region: Same as your app (e.g., `iad`)

6. **Set Secrets (Environment Variables)**

   **Via CLI:**
   ```bash
   flyctl secrets set \
     FLASK_ENV=production \
     YAHOO_CLIENT_ID=<your-client-id> \
     YAHOO_CLIENT_SECRET=<your-client-secret> \
     YAHOO_ACCESS_TOKEN=<from-oauth-setup> \
     YAHOO_REFRESH_TOKEN=<from-oauth-setup> \
     LEAGUE_ID=<your-league-id> \
     WAFFLE_BOWL_TEAMS=6 \
     CACHE_LIVE_SCORES=10 \
     NFL_SEASON=2025
   ```

   **Via Web UI:**
   - Go to your app → **Secrets**
   - Add each secret individually (or import from .env)

7. **Update Yahoo Developer Redirect URI**
   - Get your Fly.io app URL (e.g., `https://wafflebowl.fly.dev`)
   - Go to [Yahoo Developer Apps](https://developer.yahoo.com/apps/)
   - Update Redirect URI to: `https://your-app.fly.dev/auth/callback`

8. **Deploy!**
   ```bash
   flyctl deploy
   ```

   Your app will be live at `https://your-app.fly.dev`!

9. **Open Your App**
   ```bash
   flyctl open
   ```

### How Token Refresh Works

The app automatically handles Yahoo OAuth token refresh using persistent storage:

1. **First Deployment**:
   - `init_tokens.py` creates token file from environment variables
   - Tokens stored in `/root/.yf_token_store/oauth2.json` (on volume)

2. **Token Refresh**:
   - YFPY automatically refreshes tokens when they expire
   - Refreshed tokens written to the persistent volume
   - **No manual intervention needed!**

3. **Container Restarts**:
   - Volume persists tokens across restarts
   - App uses existing (refreshed) tokens
   - Token refresh continues automatically

**You'll never need to manually update tokens again!** 🎉

---

## Year-Over-Year Reusability 🔄

**The app is designed to be used season after season with minimal effort!**

### End of Season (After Playoffs)

**Fly.io scales to zero automatically**, so you only pay for what you use. With the free tier and `auto_stop_machines = true` in `fly.toml`, your app will:
- Stop running when idle (no traffic)
- **Cost $0 in the off-season** 🎉

If you want to explicitly stop it:
```bash
# Scale down to 0 machines
flyctl scale count 0

# Or suspend the app entirely
flyctl apps suspend wafflebowl
```

### Start of Next Season

1. **Check Your League ID**
   - Go to your Yahoo Fantasy league
   - Check the URL for the league ID
   - If it changed (Yahoo sometimes creates new IDs for new seasons):
     ```bash
     flyctl secrets set LEAGUE_ID=<new-league-id>
     ```

2. **Resume the App** (if suspended)
   ```bash
   # Resume app
   flyctl apps resume wafflebowl

   # Or scale back up
   flyctl scale count 1
   ```

   Or just visit your app URL - it'll auto-start on first request!

3. **Verify OAuth Tokens**
   - Tokens are stored in the persistent volume
   - They should auto-refresh automatically
   - If you get auth errors (rare):
     ```bash
     # Re-run OAuth setup locally
     python -m app.utils.oauth_setup

     # Update secrets on Fly.io
     flyctl secrets set \
       YAHOO_ACCESS_TOKEN=<new-token> \
       YAHOO_REFRESH_TOKEN=<new-refresh-token>
     ```

4. **Done!** 🧇
   - Your Waffle Bowl is live for the new season
   - No code changes needed
   - Same URL as last year
   - Tokens persist automatically

### Why This Works

- **No database** - All data fetched fresh from Yahoo API
- **Stateless design** - No historical data stored
- **Auto season detection** - App detects current NFL week automatically
- **Persistent token storage** - Volume preserves refreshed tokens across seasons
- **Auto-scaling** - Scales to zero when idle, starts on first request
- **Free tier** - Fly.io free tier covers seasonal apps perfectly

### Potential Year-Over-Year Issues

| Issue | Solution |
|-------|----------|
| League ID changed | `flyctl secrets set LEAGUE_ID=<new-id>` |
| OAuth tokens expired (rare) | Re-run `python -m app.utils.oauth_setup` and update secrets |
| Yahoo API changes | Update YFPY: `pip install --upgrade yfpy`, redeploy |
| Playoff weeks shifted | App auto-detects weeks, but verify bracket timing |
| Volume deleted | Recreate volume, redeploy (tokens will reinitialize) |

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
| `CACHE_LIVE_SCORES` | Score cache time (seconds) | `15` |
| `NFL_SEASON` | Current NFL season | Auto-detected |

### Cache Strategy

- **Live scores**: 15 seconds (configurable via `CACHE_LIVE_SCORES`)
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
curl http://localhost:5000/api/cache/clear
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
- Use ngrok: `ngrok http 5000`
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
