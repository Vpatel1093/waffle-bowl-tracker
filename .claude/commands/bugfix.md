---
description: Guide me through fixing a production bug with the standard workflow
---

I need help fixing a production bug. Follow this workflow:

## Bug Fix Workflow

### 1. Identify & Understand
- Ask me to describe the bug
- Read the relevant files (likely `bracket_service.py`, `yahoo_service.py`, or API routes)
- Understand the current implementation
- Identify where the bug likely exists

### 2. Create Tests First
- Create a mock test file (`test_<feature>_fix.py`) to verify expected behavior
- Test should show the bug and expected fix
- Run the mock test: `python test_<feature>_fix.py`

### 3. Fix the Bug
- Make the minimal fix needed
- Update comments to explain the logic
- Preserve existing functionality

### 4. Test Locally
- Run mock test to verify fix
- Start Docker: `make dev` (or ensure it's running)
- Test with real Yahoo data using Flask shell or a test script
- Verify the fix works with actual data

### 5. Test with Real Data
**REQUIRED BEFORE SEEKING APPROVAL**

Use one of these methods:
```bash
# Method 1: Flask shell
make flask-shell
# Then run test code

# Method 2: Test script
docker compose exec app python test_<feature>_real.py

# Method 3: Test in browser (for UI fixes)
# Visit http://localhost:8080 and verify the fix
```

Verify:
- ✅ Fix works with real data
- ✅ Edge cases handled
- ✅ No regressions
- ✅ UI displays correctly (for frontend fixes)

**DO NOT skip testing - I will ask if you tested it!**

### 6. Review Before Deploy
- Show me all changes
- Explain what was fixed and why
- **Confirm you tested it** with real data/in browser
- Wait for my approval before committing or deploying

### 7. Deploy (After Approval)
- Commit with detailed message including test results
- Push to GitHub: `git push origin main`
- Deploy: `make deploy`
- Verify on production: https://waffle-bowl-tracker.fly.dev

## Important Reminders

- **Read files first** - Never modify code you haven't read
- **Test with real data** - Mock tests alone aren't enough
- **Wait for approval** - Don't commit or deploy without my review
- **Minimal changes** - Fix the bug, don't refactor
- **Document the fix** - Clear commit messages with test evidence

## Common Bug Locations

- **Bracket logic**: `app/services/bracket_service.py`
- **Yahoo API**: `app/services/yahoo_service.py`
- **API endpoints**: `app/blueprints/api/routes.py`
- **Frontend**: `app/templates/components/bracket.html`

## If OAuth Tokens Expired

If you see `token_expired` errors:
```bash
./scripts/tokens/manual-oauth.sh
# I'll provide the verification code
```
