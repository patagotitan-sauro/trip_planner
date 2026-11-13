.DEFAULT_GOAL := help
COMPOSE ?= docker compose
EXEC := $(COMPOSE) exec app

.PHONY: help init bootstrap up down logs shell migrations migrate superuser prod-up backup restore lint test check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

init: ## Create .env from .env.example (does not overwrite)
	@test -f .env || cp .env.example .env
	@echo ".env ready - set DJANGO_SECRET_KEY before running"

bootstrap: init ## One-time: create the Django project (config/) and base folders
	$(COMPOSE) run --rm app django-admin startproject config .
	mkdir -p apps servicos/integracoes tests
	touch apps/__init__.py servicos/__init__.py servicos/integracoes/__init__.py tests/__init__.py

up: ## Build and start (development)
	$(COMPOSE) up -d --build

down: ## Stop (keeps the data volume; never use down -v without confirmation)
	$(COMPOSE) down

logs: ## Follow app logs
	$(COMPOSE) logs -f app

shell: ## Shell inside the app container
	$(EXEC) sh

migrations: ## Create migrations
	$(EXEC) python manage.py makemigrations

migrate: ## Apply migrations
	$(EXEC) python manage.py migrate

superuser: ## Create an admin user
	$(EXEC) python manage.py createsuperuser

prod-up: ## Production-like run, without the dev override
	$(COMPOSE) -f compose.yaml up -d --build

backup: ## Back up the database (prod: make backup COMPOSE="docker compose -f compose.yaml")
	COMPOSE="$(COMPOSE)" bash scripts/backup.sh

restore: ## Restore the database: make restore FILE=path/to/backup.sqlite3 (asks SIM)
	COMPOSE="$(COMPOSE)" bash scripts/restore.sh "$(FILE)"

lint: ## Check style, security rules and float-for-money (changes nothing)
	$(EXEC) ruff check .
	$(EXEC) ruff format --check .
	$(EXEC) python scripts/check_money_floats.py

test: ## Run the tests
	$(EXEC) pytest

check: lint ## Lint, Django checks and tests
	$(EXEC) python manage.py check
	$(EXEC) python manage.py makemigrations --check --dry-run
	$(MAKE) test
