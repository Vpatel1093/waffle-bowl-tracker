.PHONY: up down build logs shell flask-shell dev deploy refresh-tokens

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
