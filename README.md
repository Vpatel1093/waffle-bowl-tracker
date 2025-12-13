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

1. **Install Fly.io CLI**
   ```bash
   # macOS
   brew install flyctl

   # Or use install script
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly.io**
   ```bash
   flyctl auth login
   ```

3. **Create Upstash Redis** (for caching)
   ```bash
   fly redis create
   # Follow prompts to create Redis instance
   # Save the REDIS_URL for later
   ```

4. **Create Persistent Volume** (for OAuth token storage)
   ```bash
   flyctl volumes create yahoo_tokens --size 1 --region iad --app waffle-bowl-tracker
   ```

   **Why?** Yahoo OAuth tokens refresh automatically, but need persistent storage to survive container restarts.

5. **Get Fresh OAuth Tokens** (CRITICAL STEP!)

   **⚠️ IMPORTANT:** You must do this step **immediately before** setting secrets in step 6. Yahoo access tokens expire in ~1 hour!

   ```bash
   # On your LOCAL machine, run oauth setup
   cd waffle-bowl-tracker
   python -m app.utils.oauth_setup

   # This opens your browser for Yahoo authorization
   # After authorizing, tokens are saved to ~/.yf_token_store/token.json

   # Immediately copy the tokens:
   cat ~/.yf_token_store/token.json
   ```

   You'll see something like:
   ```json
   {
     "access_token": "YbZLBxmftF...",
     "refresh_token": "AIiXPGl5xWmggPSL...",
     "consumer_key": "dj0yJmk9...",
     "consumer_secret": "3ec799f2...",
     "guid": null,
     "token_time": 1765608310.327566,
     "token_type": "bearer"
   }
   ```

   **Copy the `access_token` and `refresh_token` values** - you'll need them in the next step!

6. **Set Secrets** (immediately after getting tokens!)

   **⏱️ TIME SENSITIVE:** Run this within 5 minutes of step 5 to avoid token expiry!

   ```bash
   flyctl secrets set \
     FLASK_ENV=production \
     YAHOO_CLIENT_ID=<your-client-id-from-yahoo-developer> \
     YAHOO_CLIENT_SECRET=<your-client-secret-from-yahoo-developer> \
     YAHOO_ACCESS_TOKEN=<paste-access-token-from-step-5> \
     YAHOO_REFRESH_TOKEN=<paste-refresh-token-from-step-5> \
     REDIS_URL=<redis-url-from-step-3> \
     LEAGUE_ID=<your-yahoo-league-id> \
     WAFFLE_BOWL_TEAMS=6 \
     CACHE_LIVE_SCORES=15 \
     -a waffle-bowl-tracker
   ```

7. **Deploy!**
   ```bash
   fly deploy -a waffle-bowl-tracker
   ```

   Your app will be live at `https://waffle-bowl-tracker.fly.dev`!

8. **Verify Deployment**
   ```bash
   # Watch the logs
   fly logs -a waffle-bowl-tracker

   # You should see:
   # "📝 Creating private.json with consumer credentials..."
   # "✅ Created /root/.yf_token_store/private.json"
   # "📝 Initializing Yahoo OAuth tokens from environment variables..."
   # "✅ Token file created at /root/.yf_token_store/token.json"

   # NO "Enter verifier" prompts = success!

   # Open your app
   fly open -a waffle-bowl-tracker
   ```

### Troubleshooting Deployment

#### "Token Expired" Error
If you see `OAuth oauth_problem="token_expired"` in the logs:

1. **Get fresh tokens** (tokens expire in ~1 hour):
   ```bash
   # On local machine
   python -m app.utils.oauth_setup
   cat ~/.yf_token_store/token.json
   ```

2. **Update secrets immediately**:
   ```bash
   flyctl secrets set \
     YAHOO_ACCESS_TOKEN="<new-access-token>" \
     YAHOO_REFRESH_TOKEN="<new-refresh-token>" \
     -a waffle-bowl-tracker
   ```

3. **Clean token file and restart**:
   ```bash
   fly ssh console -a waffle-bowl-tracker
   rm /root/.yf_token_store/token.json
   exit

   fly apps restart waffle-bowl-tracker
   ```

#### "Enter Verifier" Prompts in Logs
This means token files are missing or invalid. Follow the "Token Expired" steps above.

#### Debugging Commands
```bash
# SSH into app
fly ssh console -a waffle-bowl-tracker

# Check token files
ls /root/.yf_token_store/
cat /root/.yf_token_store/token.json

# Check secrets are set
env | grep YAHOO

# View logs
fly logs -a waffle-bowl-tracker

# Connect to Redis
fly redis connect
```

### How Token Refresh Works

The app automatically handles Yahoo OAuth token refresh using persistent storage:

1. **First Deployment**:
   - `init_tokens.py` creates token files from environment variables
   - Files created: `private.json` (consumer credentials) and `token.json` (OAuth tokens)
   - Both stored in `/root/.yf_token_store/` (on persistent volume)

2. **Automatic Token Refresh**:
   - YFPY automatically refreshes tokens when they expire (tokens expire every ~1 hour)
   - Refreshed tokens are written back to `token.json` on the persistent volume
   - The refresh_token is long-lived and enables automatic renewal

3. **Container Restarts**:
   - Persistent volume preserves `token.json` across restarts
   - App uses existing (possibly refreshed) tokens
   - Token refresh continues automatically

**After initial deployment, you'll never need to manually update tokens again!** 🎉

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
