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
	@echo "Preparing to deploy to Fly"
	@sh -ec ' \
		# Resolve app name: prefer environment, otherwise try fly.toml \
		if [ -n "$$FLY_APP" ]; then \
			echo "Using FLY_APP from env: $$FLY_APP"; \
		else \
			if [ -f fly.toml ]; then \
				FLY_APP=$$(grep -E "^app[[:space:]]*=" fly.toml | sed -E "s/app[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\\1/" | head -n1); \
				if [ -n "$$FLY_APP" ]; then \
					echo "Detected Fly app from fly.toml: $$FLY_APP"; \
				else \
					echo "Could not determine Fly app from fly.toml; please set FLY_APP or add 'app = \"your-app\"' to fly.toml"; exit 1; \
				fi; \
			else \
				echo "FLY_APP not set and fly.toml not found; use: FLY_APP=<app> make deploy or add 'app = \"your-app\"' to fly.toml"; exit 1; \
			fi; \
		fi; \
		# Ensure helper is executable and run it to push tokens/secrets (interactive) \
		chmod +x ./scripts/tokens/push-to-fly.sh || true; \
		echo "Running ./scripts/tokens/push-to-fly.sh $$FLY_APP to update Fly secrets..."; \
		./scripts/tokens/push-to-fly.sh "$$FLY_APP"; \
		# Deploy the app \
		echo "Deploying to Fly: $$FLY_APP"; \
		flyctl deploy -a "$$FLY_APP"; \
	'
