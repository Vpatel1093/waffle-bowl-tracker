# Waffle Bowl Tracker - Development Guide

## Project Overview
Fantasy football "losers bracket" tracker for the worst teams competing in the Waffle Bowl. Built with Flask, Yahoo Fantasy API, and Docker.

The Waffle Bowl is a single-elimination tournament where LOSING advances you (worst of the worst wins). The bottom 6 teams from the regular season compete across weeks 15-17 of the NFL season to determine who finishes in last place.

## Development Commands

### Docker & Make Commands
**Always use these commands - the app runs in Docker!**

- `make dev` - Start development server with live logs (foreground)
- `make up` - Start server in background
- `make down` - Stop all containers
- `make logs` - View container logs (tail last 200 lines)
- `make build` - Rebuild Docker images
- `make shell` - Open shell inside running container
- `make flask-shell` - Open Flask shell for testing Python code
- `make deploy` - Deploy to Fly.io
- `make refresh-tokens` - Refresh Yahoo OAuth tokens locally
- `make test-bracket` - Run mock bracket tests (no API calls)
- `make test-real` - Test bracket with real Yahoo data
- `make verify-bracket` - Quick check of current Waffle Bowl teams

### Testing Code Changes

**Important:** Real data testing only works during **NFL weeks 15-17** when the Waffle Bowl is active. Outside these weeks, you'll need to use mock/stub data or the tests will show empty brackets.

To test Python code with the Yahoo API:
```bash
make flask-shell
# Then inside the Flask shell:
from app.services.bracket_service import BracketService
from app.services.yahoo_service import YahooService
# ... run your test code
```

### Environment Setup
- Yahoo OAuth credentials stored in `.env` file
- Tokens managed via `refresh-tokens` script
- Configuration in `app/config.py`

## Project Structure

### Key Files
- `app/services/bracket_service.py` - Core Waffle Bowl bracket logic
- `app/services/yahoo_service.py` - Yahoo Fantasy API integration
- `app/blueprints/api/routes.py` - API endpoints
- `app/templates/` - Jinja2 templates with waffle-themed styling

### Bracket Logic (BracketService)
- **Seeding**: Seeds 1-6, where Seed 1 = worst team, Seed 6 = best of worst
- **Quarterfinals (Week 15)**: Seeds 3v6, 4v5 (Seeds 1-2 get byes)
- **Semifinals (Week 16)**: QF losers play bye teams
  - Better QF loser (higher seed) plays Seed 1 (easiest matchup)
  - Worse QF loser (lower seed) plays Seed 2 (harder matchup)
- **Finals (Week 17)**: SF losers compete for last place

## Common Workflows

### After Code Changes
1. Changes auto-reload if using `make dev`
2. Or: `make down && make up` to restart

### Debugging
1. Check logs: `make logs`
2. Enter container: `make shell`
3. Test in Flask shell: `make flask-shell`

### Before Deployment
1. Test locally: `make dev`
2. Check Docker build: `make build`
3. Deploy: `make deploy`

## Architecture

### Application Stack
- **Backend**: Flask (Python 3.12)
- **API Integration**: Yahoo Fantasy Sports API (via yfpy library)
- **Caching**: Redis (for API response caching)
- **Deployment**: Fly.io (Docker containers)
- **Frontend**: Server-side rendered Jinja2 templates with Tailwind CSS

### Data Flow
1. **Yahoo API** → `YahooService` → Fetch league standings, scoreboard data
2. **BracketService** → Process standings → Determine Waffle Bowl participants
3. **BracketService** → Update bracket with weekly scores → Determine losers
4. **API Routes** → Serve bracket data to frontend
5. **Templates** → Render bracket visualization with live scores

### Key Services

#### YahooService (`app/services/yahoo_service.py`)
- Handles OAuth authentication with Yahoo
- Fetches league standings (team records, points)
- Fetches weekly scoreboard data (matchup scores, game status)
- Caches API responses to reduce rate limit issues
- Token auto-refresh on expiration

#### BracketService (`app/services/bracket_service.py`)
- **`get_waffle_bowl_teams()`**: Identifies bottom 6 teams from standings
- **`create_bracket_structure()`**: Sets up 3-round tournament structure
- **`update_bracket_with_results()`**: Updates bracket with weekly scores and determines losers
- **`is_week_complete()`**: Checks if all games in a week are finished
- **Core Logic**: Week detection, loser advancement, score tracking by week

### File Organization

```
app/
├── services/
│   ├── bracket_service.py    # Waffle Bowl bracket logic
│   └── yahoo_service.py       # Yahoo API integration
├── blueprints/
│   ├── api/routes.py          # API endpoints (/api/bracket, /api/scoreboard)
│   └── main/routes.py         # Frontend routes (/, /bracket)
├── templates/
│   ├── bracket.html           # Main bracket page
│   ├── components/
│   │   ├── bracket.html       # Bracket visualization
│   │   └── matchup_details.html  # Head-to-head modals
├── utils/
│   └── oauth_setup.py         # OAuth token refresh utility
└── config.py                  # App configuration

scripts/
└── tokens/
    ├── refresh-local.sh       # Refresh OAuth tokens locally
    ├── manual-oauth.sh        # Manual OAuth flow helper
    └── push-to-fly.sh         # Push tokens to Fly.io secrets
```

## Waffle Bowl Business Logic

### Tournament Structure (6 teams, 3 weeks)

**Regular Season Standings → Waffle Bowl Seeds**
- Bottom 6 teams by record (fewest wins)
- Tiebreaker: Lower points_for = worse team
- Seed 1 = Worst team | Seed 6 = Best of the worst

**Week 15 (Quarterfinals)**
- Matchup 1: Seed 3 vs Seed 6
- Matchup 2: Seed 4 vs Seed 5
- Seeds 1-2 get BYES (worst teams skip this round)
- **Losers advance to semifinals**

**Week 16 (Semifinals)**
- SF1: Worse QF loser vs Seed 2 (harder matchup)
- SF2: Better QF loser vs Seed 1 (easier matchup - reward for better regular season)
- **Logic**: Higher seed number = better team → gets easier opponent
- **Losers advance to finals**

**Week 17 (Finals)**
- SF losers compete head-to-head
- **Loser = LAST PLACE** 🧇

### Critical Business Rules

1. **Seeding Matters**: In a losers bracket, Seed 1 is the WORST team (easiest opponent)
2. **Better Teams Rewarded**: QF loser with higher seed gets easier SF matchup
3. **Week Completion**: Must wait for all games to finish before determining losers
4. **Score Tracking**: Each team's score is tracked per week in `points_by_week`

### Common Edge Cases

- **Ties**: Currently no tie-breaking logic (rare in fantasy football)
- **Incomplete Weeks**: Bracket shows TBD until week is complete
- **Token Expiration**: Yahoo tokens expire, auto-refresh via yfpy
- **Missing Scores**: Falls back to 0.0 if team not in scoreboard data

## Production Bug Fix Workflow

### Standard Process (Reference from our semifinal fix)

1. **Identify & Reproduce**
   - Read the relevant service files (`bracket_service.py`, `yahoo_service.py`)
   - Understand the current logic
   - Identify the bug location

2. **Create Tests**
   - Write mock test first (no API calls needed)
   - Verify expected behavior vs actual behavior

3. **Fix & Test Locally**
   - Make the fix
   - Run mock test: `python test_<feature>.py`
   - Start Docker: `make dev`
   - Test with real data using Flask shell or test script

4. **Verify with Real Data**
   - **Note:** Only works during NFL weeks 15-17 when Waffle Bowl is active
   - Use `make flask-shell` or `docker compose exec app python test_script.py`
   - Confirm fix works with actual Yahoo API data
   - Check edge cases

5. **Deploy**
   - Commit changes with detailed message
   - Push to GitHub: `git push origin main`
   - Deploy: `make deploy`
   - Verify on production: https://waffle-bowl-tracker.fly.dev

### Testing Commands

**Run Flask shell for interactive testing:**
```bash
make flask-shell
# Inside shell:
from app.services.bracket_service import BracketService
from app.services.yahoo_service import YahooService
yahoo = YahooService()
bracket_service = BracketService()
# Test your code...
```

**Run test script inside Docker:**
```bash
docker compose exec app python test_script.py
```

**Check logs for errors:**
```bash
make logs
```

## OAuth Token Management

### When Tokens Expire

Tokens expire periodically. You'll see: `OAuth oauth_problem="token_expired"`

**Refresh tokens:**
1. Run: `./scripts/tokens/manual-oauth.sh`
2. Open the authorization URL in browser
3. Authorize the app
4. Copy the verification code
5. Paste into terminal
6. Tokens automatically saved to `.env` and Docker

**Manual OAuth URL:**
```
https://api.login.yahoo.com/oauth2/request_auth?redirect_uri=oob&response_type=code&client_id=<YOUR_CLIENT_ID>
```

### Deployment Token Update

After refreshing tokens locally, update Fly.io:
```bash
make deploy  # Automatically pushes .env secrets to Fly
```
