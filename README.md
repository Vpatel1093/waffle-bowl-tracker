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

## Railway Deployment

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

2. **Create Railway Project**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your waffle-bowl-tracker repository

3. **Add Redis Service**
   - In Railway project, click "+ New"
   - Select "Redis"
   - Railway will provide a `REDIS_URL`

4. **Set Environment Variables**
   In Railway project settings, add:
   ```
   FLASK_ENV=production
   YAHOO_CLIENT_ID=<your-client-id>
   YAHOO_CLIENT_SECRET=<your-client-secret>
   YAHOO_ACCESS_TOKEN=<from-oauth-setup>
   YAHOO_REFRESH_TOKEN=<from-oauth-setup>
   REDIS_URL=<from-railway-redis>
   LEAGUE_ID=<your-league-id>
   WAFFLE_BOWL_TEAMS=6
   ```

5. **Update Yahoo Developer Redirect URI**
   - Get your Railway app URL (e.g., `https://waffle-bowl-tracker.up.railway.app`)
   - Update Yahoo Developer app redirect URI to: `https://your-app.railway.app/auth/callback`

6. **Deploy**
   - Railway auto-deploys on git push
   - Your app will be live at the Railway URL!

---

## Year-Over-Year Reusability 🔄

**The app is designed to be used season after season with minimal effort!**

### End of Season (After Playoffs)

1. Go to [Railway Dashboard](https://railway.app)
2. Find your Waffle Bowl project
3. Click **"Pause"** or **"Stop"** the app
4. **No charges while paused** (free tier!)

### Start of Next Season

1. **Check Your League ID**
   - Go to your Yahoo Fantasy league
   - Check the URL for the league ID
   - If it changed (Yahoo sometimes creates new IDs for new seasons):
     - Update `LEAGUE_ID` in Railway environment variables

2. **Resume the App**
   - Go to Railway dashboard
   - Click **"Resume"** or **"Start"** your Waffle Bowl project

3. **Verify OAuth Tokens**
   - The app should auto-refresh tokens
   - If you get auth errors, re-run the OAuth setup:
     ```bash
     python -m app.utils.oauth_setup
     ```
   - Update `YAHOO_ACCESS_TOKEN` and `YAHOO_REFRESH_TOKEN` in Railway

4. **Done!** 🧇
   - Your Waffle Bowl is live for the new season
   - No code changes needed
   - Same URL as last year

### Why This Works

- **No database** - All data fetched fresh from Yahoo API
- **Stateless design** - No historical data stored
- **Auto season detection** - App detects current NFL week automatically
- **Token refresh** - OAuth tokens auto-refresh (should last year-to-year)
- **Free hosting** - Railway's free tier is perfect for seasonal apps

### Potential Year-Over-Year Issues

| Issue | Solution |
|-------|----------|
| League ID changed | Update `LEAGUE_ID` env var in Railway |
| OAuth tokens expired | Re-run `python -m app.utils.oauth_setup` |
| Yahoo API changes | Check for YFPY library updates: `pip install --upgrade yfpy` |
| Playoff weeks shifted | App auto-detects weeks, but verify bracket timing |

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
- **Caching**: Redis 5.2.0 (fast caching layer)
- **Deployment**: Railway + Gunicorn

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
