# Project files: what each one is for

Short and basic. Grouped by purpose. Keep it updated when a file is added or removed.

## Repository hygiene

| File | Why it exists |
|---|---|
| `.gitignore` | Keeps secrets, the database, caches and virtual environments out of Git. |
| `.editorconfig` | Gives every editor the same indentation, line endings and final newline. |
| `LICENSE` | States the terms under which others may use the code. |

## Dependencies

| File | Why it exists |
|---|---|
| `requirements.txt` | Packages needed to run the app (Django, gunicorn, whitenoise). |
| `requirements-dev.txt` | Adds tools for development only (pytest, ruff, debugpy). Not installed in production. |

## Docker and Compose

| File | Why it exists |
|---|---|
| `Dockerfile` | Builds the image in three stages: `base` (runtime), `dev` (adds test and lint tools) and `prod` (code baked in, runs gunicorn). |
| `docker/entrypoint.sh` | Runs before the main command: applies migrations and, in production, collects static files. Skips both if `manage.py` is missing. |
| `.dockerignore` | Keeps `.git`, `.env`, caches and the database out of the build context and the image. |
| `compose.yaml` | Production-like setup: one service, the `dados` volume for the SQLite file, port bound by `APP_BIND` and `APP_PORT`. |
| `compose.override.yaml` | Loaded automatically in development: mounts the code, runs `runserver` with debug on, forces the port to `127.0.0.1`. |
| `.env.example` | Template for the environment variables. Copy it to `.env` (`make init`) and fill it in. `.env` is never committed. |

## Commands

| File | Why it exists |
|---|---|
| `Makefile` | One entry point for common tasks (`make up`, `make migrate`, `make shell`). Run `make help` for the list. |

## Django project

| Path | Why it exists |
|---|---|
| `manage.py` | Django's command-line tool (migrate, createsuperuser, runserver). |
| `config/settings.py` | All configuration. Everything environment-specific is read from environment variables. |
| `config/urls.py` | Top-level URL routing. |
| `config/wsgi.py` | Entry point gunicorn uses to serve the app. |
| `config/asgi.py` | Entry point for async servers. Not used yet. |
| `apps/` | The Django apps (models, views, forms, templates). Thin, no business rules. |
| `servicos/` | Business rules in pure Python (money, conversion, splitting, planned vs actual). No HTTP. |
| `servicos/integracoes/` | External APIs (for example exchange rates) behind an interface. |
| `tests/` | Automated tests. |

The `__init__.py` files only mark these folders as Python packages.

## Quality

| File | Why it exists |
|---|---|
| `ruff.toml` | Lint and format rules, including security (`S`) and naive-datetime (`DTZ`) checks. |
| `pytest.ini` | Tells pytest where the tests are and which Django settings to use. |
| `scripts/check_money_floats.py` | Fails when `float` is used for money in `apps/` and `servicos/` (the Decimal rule). |
| `.pre-commit-config.yaml` | Runs ruff and the float check on staged files before each commit, inside the container. Install once per clone with `pre-commit install`. |

## Instructions for AI assistants

| File | Why it exists |
|---|---|
| `AGENTS.md` | The single project guide for any AI assistant: rules, architecture, money and database rules. |
| `.claude/CLAUDE.md` | Points Claude Code to `AGENTS.md`. |
| `.github/copilot-instructions.md` | Points GitHub Copilot to `AGENTS.md`. |