.PHONY: up down check migrate seed
up:
	docker compose up --build
down:
	docker compose down
check:
	npm run check
	python -m pytest apps/api/tests
migrate:
	docker compose run --rm api alembic upgrade head
seed:
	docker compose run --rm api python -m app.seed

