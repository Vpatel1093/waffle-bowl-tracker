.PHONY: up down build logs shell flask-shell dev deploy refresh-tokens test-bracket test-real verify-bracket

dev:
	docker compose up --build

up:
	docker compose up -d --build

logs:
	docker compose logs -f --tail=200

down:
	docker compose down

build:
	docker compose build

shell:
	docker compose exec app /bin/sh

flask-shell:
	docker compose exec app flask shell

refresh-tokens:
	@chmod +x ./scripts/tokens/refresh-local.sh
	@echo "Refreshing local tokens (interactive) and updating .env..."
	@./scripts/tokens/refresh-local.sh

deploy:
	@chmod +x ./scripts/deploy-to-fly.sh
	@./scripts/deploy-to-fly.sh

test-bracket:
	@echo "Running bracket logic mock tests..."
	@python test_semifinals_fix.py || echo "No mock test file found"

test-real:
	@echo "Testing bracket logic with real Yahoo data..."
	@docker compose exec -T app python test_semifinals_real.py || echo "Make sure Docker is running: make dev"

verify-bracket:
	@echo "Quick bracket verification with current data..."
	@docker compose exec -T app python -c "\
	from app import create_app; \
	from app.services.bracket_service import BracketService; \
	from app.services.yahoo_service import YahooService; \
	app = create_app(); \
	with app.app_context(): \
	    yahoo = YahooService(); \
	    bs = BracketService(); \
	    standings = yahoo.get_league_standings(); \
	    teams = bs.get_waffle_bowl_teams(standings if isinstance(standings, list) else standings.get('standings', [])); \
	    print('Waffle Bowl Teams:'); \
	    [print(f\"  Seed {t['waffle_seed']}: {t['name']}\") for t in teams]" \
	|| echo "Error: Make sure Docker is running and tokens are valid"
