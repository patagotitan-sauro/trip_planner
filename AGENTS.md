# Project guide for AI coding assistants

This file tells any AI coding assistant (Claude Code, GitHub Copilot, Cursor, Codex, and others) how to work in this repository. Tool-specific files (`CLAUDE.md`, `.github/copilot-instructions.md`) only point here, so there is a single source of truth. Keep it short and current: when something changes, update it in the same change.

## 1. Project overview

A web app to plan trips (destinations, day-by-day itinerary, estimated costs and a budget) and then track the spending of trips actually taken, comparing planned and actual costs. Later phases may add multi-currency conversion, shared expenses and reservation checklists.

- Stack: Python 3.12, Django 5.2 LTS, SQLite (WAL mode), server-rendered templates, Docker Compose, pytest.
- Requirements will live in `docs/especificacao.md` (not written yet). Do not invent requirements: ask a short, specific question or state your assumption.

## 2. Current state (update as the repo grows)

Exists: `.gitignore`, `.editorconfig`, `requirements.txt`, `requirements-dev.txt`, `Dockerfile`, `docker/entrypoint.sh`, `.dockerignore`, `.env.example`, `compose.yaml`, `compose.override.yaml`.

Not created yet: `Makefile`, the Django project, lint and test configuration, CI, skills. Do not assume they exist or run commands that depend on them.

## 3. How to work with the owner

The owner is building this environment file by file to learn.

- Work on one file or one concern at a time.
- Explain what each part does and why, and compare options with pros and cons when more than one is reasonable.
- Verify versions of dependencies and base images against current sources before recommending them. Do not rely on memory.
- Keep changes small and say how to check them.

## 4. Language and naming

- User-facing text (labels, messages, templates): Brazilian Portuguese.
- Code identifiers, comments, docstrings, commit messages: English.
- Domain terms from the specification keep their spelling, for example the planned Django app names (`contas`, `viagens`, `planejamento`, `despesas`, `relatorios`).
- Follow PEP 8 and use type hints on new functions.

## 5. Architecture (planned)

Four layers; dependencies point one way (presentation -> services -> models and integrations):

| Layer | Where | Responsibility |
|---|---|---|
| Presentation | `apps/*/views.py`, `forms.py`, `templates/` | HTTP, forms, rendering. Thin, no business rules |
| Services | `servicos/` | Business rules: money, conversion, splitting, planned-vs-actual. Pure Python, no HTTP |
| Models | `apps/*/models.py` | Entities and persistence |
| Integrations | `servicos/integracoes/` | External APIs behind an interface |

Prefer composition over inheritance, depend on interfaces, keep modules cohesive, and do not over-engineer.

## 6. Money and data rules (critical)

- Never use `float` for money. Use `decimal.Decimal` and Django `DecimalField`.
- Round in one place only (`ROUND_HALF_UP`, quantized to the currency's decimal places).
- An expense stores the original amount, currency, rate to the base currency and converted amount, converted when recorded. Later rate changes must not alter past reports.
- Split amounts so the parts add up exactly to the total, with leftover cents in a fixed, documented order.
- Store timestamps in UTC; display in `America/Sao_Paulo`.

## 7. Docker and Compose

- Project name `trip-planner`. One service `app`, one named volume `dados` holding the SQLite file at `/data/db.sqlite3`. The database never goes in the image or in Git.
- The `Dockerfile` has three stages: `base`, `dev` (adds test and lint tools) and `prod` (code baked in, runs gunicorn). Base image: `python:3.12-slim-trixie`.
- `compose.yaml` is production-like. `compose.override.yaml` is loaded automatically in development (bind mount, `runserver`, `DEBUG=1`) and forces the port to `127.0.0.1`.
- Published address and port come from `APP_BIND` (default `127.0.0.1`) and `APP_PORT` in `.env`. Exposing the app to the private network means setting `APP_BIND` to the machine's LAN IP and adding that host to `DJANGO_ALLOWED_HOSTS`. Do this only in production-like mode, never with `DEBUG` on. Docker-published ports bypass `ufw`, so the bind address is the real control.
- Never run `docker compose down -v` without explicit confirmation: it deletes the database volume.
- Images contain nothing machine-specific. Hostnames, IPs and secrets live in each machine's `.env`.

## 8. Security

- No secrets in code, commits, logs or examples. Use environment variables; `.env` is git-ignored and `.env.example` has no real values.
- Keep CSRF protection on. Every query for user data is scoped to the logged-in owner.
- `DEBUG = False` and a strict `ALLOWED_HOSTS` outside local development.
- Until HTTPS exists, do not enable secure-cookie or SSL-redirect settings (login would break over HTTP).

## 9. Ask before you do these

- Deleting data, volumes, migrations or files you did not create.
- Adding or upgrading a dependency.
- Changing the specification, the data model or a public behavior.
- Running commands that affect anything outside this repository.
- Any step you are unsure is reversible.

## 10. Git

Small, focused commits with imperative messages (for example `Add Makefile`). Never commit `.env`, database files or virtual environments. Do not rewrite shared history without explicit permission.
