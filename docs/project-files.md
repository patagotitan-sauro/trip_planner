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
| `requirements.txt` | Packages needed to run the app (Django, django-countries, gunicorn, whitenoise). |
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
| `scripts/backup.sh` | Copies the SQLite database with the backup API, checks it and keeps the latest copies in `~/backups/trip-planner`. |
| `scripts/restore.sh` | Restores a checked backup after typing `SIM`, keeping a safety backup of the current database first. |

## Django project

| Path | Why it exists |
|---|---|
| `manage.py` | Django's command-line tool (migrate, createsuperuser, runserver). |
| `config/settings.py` | All configuration. Everything environment-specific is read from environment variables. |
| `config/urls.py` | Top-level URL routing. |
| `config/wsgi.py` | Entry point gunicorn uses to serve the app. |
| `config/asgi.py` | Entry point for async servers. Not used yet. |
| `apps/` | The Django apps (models, views, forms, templates). Thin, no business rules. |
| `apps/contas/` | Login and logout with Django auth (no models). Accounts are created by the admin. |
| `apps/viagens/` | Trips, destinations and itinerary activities (models and migrations). Also the placeholder home page until the trip list exists. |
| `templates/base.html` | Base page in pt-BR (top bar with user and logout) that every page extends. |
| `static/css/pico.min.css` | Pico CSS 2.1.1 (MIT, license beside it), vendored so the UI works offline. Replace the file to upgrade. |
| `static/css/app.css` | Small project styles on top of Pico (for example the red `perigo` button for destructive actions). |
| `apps/despesas/` | Expense categories and expenses (models and migrations). |
| `servicos/` | Business rules in pure Python (money, conversion, splitting, balance allocation, trip comparison, history totals). No HTTP. |
| `servicos/integracoes/` | External APIs (for example exchange rates) behind an interface. |
| `servicos/despesas.py` | Expense rules: BRL conversion with the stored rate, IOF by payment method (RN-09 to RN-11), allowed payment methods by currency (RN-10) and totals. |
| `servicos/moeda.py` | Converts amounts to BRL and rounds money in one place. |
| `servicos/classificacao.py` | Classifies a trip as national or international from its destinations (RN-02). |
| `servicos/viagens.py` | Trip rules: grouping by state and year, date validation, who can be deleted, itinerary grouping and position (RN-03, RN-06, RN-18, RN-23). |
| `servicos/importacao_antiga.py` | Mapping rules (trip status, destinations, expense situation) for the old database import. |
| `apps/viagens/management/commands/importar_banco_antigo.py` | One-time import: reads an old `db.sqlite3` read-only and writes the new models in one transaction. |
| `tests/` | Automated tests. |

The `__init__.py` files only mark these folders as Python packages.

## Documentation

| File | Why it exists |
|---|---|
| `docs/especificacao.md` | What the app must do (in pt-BR): scope, access, currency, glossary, business rules (RN-xx), open decisions and screen requirements (RF-xx). |
| `docs/instruction.md` | Data model and how another Django project can reuse a copy of the SQLite database. Reference only, not a requirement of this project. |
| `docs/roadmap.md` | Step-by-step plan for building the app, one phase per chat. |
| `docs/project-files.md` | This file. |

## Quality

| File | Why it exists |
|---|---|
| `ruff.toml` | Lint and format rules, including security (`S`) and naive-datetime (`DTZ`) checks. |
| `pytest.ini` | Tells pytest where the tests are and which Django settings to use. |
| `scripts/check_money_floats.py` | Fails when `float` is used for money in `apps/` and `servicos/` (the Decimal rule). |
| `.pre-commit-config.yaml` | Runs ruff and the float check on staged files before each commit, inside the container. Install once per clone with `pre-commit install`. |
| `.github/workflows/ci.yml` | GitHub Actions: builds the dev image and runs `make check` on every push to `main` and on pull requests. |

## Instructions for AI assistants

| File | Why it exists |
|---|---|
| `AGENTS.md` | The single project guide for any AI assistant: rules, architecture, money and database rules. |
| `.github/copilot-instructions.md` | Points GitHub Copilot to `AGENTS.md`. |
| `.github/commit-instructions.md` | Commit message rules for Copilot (same as `AGENTS.md` section 16). |
| `.github/skills/`, `.github/agents/` | The skills and agent roles for GitHub Copilot. Edit them here. |

## Editor

| File | Why it exists |
|---|---|
| `.vscode/settings.json` | Format and organize imports with ruff on save; hide cache folders. |
| `.vscode/extensions.json` | Extensions VS Code offers to install for this project. |
| `.vscode/launch.json` | Debug configurations (Django on port 8001, current pytest file). Used inside the dev container. |
| `.devcontainer/devcontainer.json` | Opens VS Code inside the `app` container, so imports, ruff and tests use the real environment. |
