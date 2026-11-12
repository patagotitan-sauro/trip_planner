# Project guide for AI coding assistants

This file tells any AI coding assistant (Claude Code, GitHub Copilot, Cursor, Codex, and others) how to work in this repository. Tool-specific file `.github/copilot-instructions.md` only points here, so there is a single source of truth. Keep it short and current: when something changes, update it in the same change.

## 1. Project overview

A family web app to study possible trips and decide which one to take (destinations, day-by-day itinerary, estimated costs and a budget), manage the expenses of the chosen trip (including allocation of prepaid card and cash balances), and keep a history of completed trips with their costs. Later phases may add shared expenses and reservation checklists.

- Stack: Python 3.12, Django 5.2 LTS, SQLite (WAL mode), server-rendered templates, Docker Compose, pytest.
- Requirements and business rules live in `docs/especificacao.md`. Rules such as IOF and trip classification are cited there as RN-xx; do not copy their values here. 
- If the code and the specification disagree, do not silently pick one. Point out the difference and ask. 

## 2. Current state (update as the repo grows)

Exists: `.gitignore`, `.editorconfig`, `requirements.txt`, `requirements-dev.txt`, `Dockerfile`, `docker/entrypoint.sh`, `.dockerignore`, `.env.example`, `compose.yaml`, `compose.override.yaml`, `Makefile`, the Django project (`manage.py`, `config/`, empty `apps/`, `servicos/`, `servicos/integracoes/`, `tests/`), `ruff.toml`, `pytest.ini`, `scripts/check_money_floats.py`, `.pre-commit-config.yaml`, `docs/project-files.md`, `docs/especificacao.md`, `make lint` / `make test` / `make check`, `tests/test_settings.py` (settings smoke tests), `.github/workflows/ci.yml` (runs `make check` on push and pull request), `.github/skills/`, `.github/agents/` (skills and agent roles), `.vscode/`, `.devcontainer/`.

Not created yet: any Django app, tests for business rules. Do not assume they exist or run commands that depend on them.

## 3. Communication style

- Write clear, objective, educational explanations in English.
- Explain the reasoning behind technical decisions, not only what the code does.
- When more than one reasonable approach exists, compare the options with pros and cons and recommend one.
- Adapt examples to this project: its data volume (small, personal or family use), its file structure, its database (SQLite), its integrations (exchange-rate API) and its constraints.
- When proposing charts or visualizations, match the chart type to the business question, the data type and the audience.

## 4. How to work

The owner is building this environment file by file to learn.

1. **Understand first.** Read the relevant files, and the specification section once it exists, before editing.
2. **Start simple, then improve.** Deliver the simplest version that works, then propose improvements as separate steps.
3. **Keep changes small.** One concern per change, one file at a time, no unrelated refactoring.
4. **Do not invent requirements.** If something is ambiguous or missing, ask a short, specific question or state the assumption you are making.
5. **Plan large changes.** For anything touching several files or the database schema, outline the plan first and wait for confirmation.
6. **Verify.** Run the checks that exist (see "Current state"), report what you ran and the result, and say if you could not run something. Say how the owner can check each change.
7. **Verify versions.** Check dependency and base-image versions against current sources before recommending them. Do not rely on memory.

## 5. Commands

The `Makefile` is the single entry point; run `make help` for the list. Everything runs inside Docker Compose.

| Command | What it does |
|---|---|
| `make init` | Create `.env` from `.env.example` (never overwrites) |
| `make bootstrap` | One-time: create the Django project (`config/`) and base folders |
| `make up` / `make down` | Build and start (development) / stop, keeping the data volume |
| `make logs` / `make shell` | Follow logs / open a shell in the container |
| `make migrations` / `make migrate` | Create / apply migrations |
| `make superuser` | Create an admin user |
| `make prod-up` | Production-like run, without the dev override |
| `make lint` | `ruff check`, `ruff format --check` and the float-for-money check; changes nothing |
| `make test` | Run pytest |
| `make check` | `make lint`, `manage.py check`, `makemigrations --check --dry-run`, then `make test` |

The float check fails on `float` used for money in `apps/` and `servicos/` (escape hatch: `# allow-float: reason`). `pre-commit run --all-files` runs the same lint and float checks as the commit hook (host tool, needs the container running; `pre-commit install` once per clone).

Backup commands arrive later. Do not assume they exist until "Current state" lists them.

## 6. Language and naming

- User-facing text (labels, messages, templates): Brazilian Portuguese.
- Code identifiers, comments, docstrings, commit messages: English.
- Domain terms from the specification keep their spelling, for example the planned Django app names (`contas`, `viagens`, `planejamento`, `despesas`, `relatorios`).
- Follow PEP 8 and use type hints on new functions.

## 7. Architecture (planned)

Four layers; dependencies point one way (presentation -> services -> models and integrations):

| Layer | Where | Responsibility |
|---|---|---|
| Presentation | `apps/*/views.py`, `forms.py`, `templates/` | HTTP, forms, rendering. Thin, no business rules |
| Services | `servicos/` | Business rules: money, conversion, splitting, balance allocation, trip comparison, history totals. Pure Python, no HTTP |
| Models | `apps/*/models.py` | Entities and persistence |
| Integrations | `servicos/integracoes/` | External APIs behind an interface. Exchange-rate suggestion: Frankfurter (`api.frankfurter.dev`), no API key |

## 8. Design principles

Apply these when designing or refactoring:

- **Encapsulate what varies.** Isolate the parts likely to change.
- **Favor composition over inheritance.** Inherit only for a true "is-a" relationship.
- **Program to interfaces, not implementations.** Depend on abstractions (protocols or abstract base classes).
- **Keep coupling low and cohesion high.** A module should have one clear reason to exist.

SOLID, applied to reusable modules, classes and services:

- **S**ingle responsibility: one reason to change per class or module.
- **O**pen/closed: extend behavior by adding code, not by editing stable code.
- **L**iskov substitution: a subtype must work wherever its base type is expected.
- **I**nterface segregation: prefer several small interfaces to one large one.
- **D**ependency inversion: high-level code depends on abstractions, not on concrete details.

Do not over-engineer. Use a pattern only when it solves a real problem present now.

## 9. Code quality

- Prioritize readability: small functions, clear names, no clever tricks.
- Separate concerns: do not mix parsing, validation, business rules and rendering in the same function.
- Handle errors deliberately: validate input at the boundary, raise specific exceptions, never swallow errors silently, and show the user a clear message.
- Design for testability: pure functions and injected dependencies instead of hidden global state.
- Remove dead code and unused imports. Do not leave commented-out code.
- Comments explain why, not what.

## 10. Testing

pytest and pytest-django are in the dev image and configured in `pytest.ini` (tests live in `tests/`). Only the settings smoke tests exist so far.

- Test business rules in `servicos/` with unit tests first. They need no database or HTTP.
- Cover edge cases for money: zero, negative values, rounding, currencies with different decimal places, and splits that do not divide evenly.
- Every bug fix includes a regression test that fails before the fix.
- Tests are deterministic: no real network calls (mock the exchange-rate API), no dependence on the current date unless it is injected.
- Name tests by behavior, for example `test_split_gives_remainder_to_first_participants`.

## 11. Money and data rules (critical)

- Never use `float` for money. Use `decimal.Decimal` and Django `DecimalField`.
- Round in one place only (`ROUND_HALF_UP`, quantized to the currency's decimal places).
- An expense stores the original amount, currency, rate to the base currency, converted amount, IOF rate and IOF amount, all converted when recorded. Later rate changes must not alter past reports.
- Split amounts so the parts add up exactly to the total, with leftover cents in a fixed, documented order.
- Store timestamps in UTC; display in `America/Sao_Paulo`.
- Exchange rates need more precision than amounts (for example 8 decimal places).
- Balance allocation follows RN-14, RN-16 and RN-17 in the spec. Keep the calculation in one service function and test it.
- Open decisions (spec section 6): confirm the proposals there before implementing the rules they affect.

## 12. Database (SQLite)

- Enable WAL mode. Run a single app instance against the file.
- Commit all migrations. Never edit or delete an applied migration; create a new one.
- Make schema changes backward compatible when possible, and warn before any change that can lose data.
- Backups use the SQLite backup API, not a plain file copy while the app is running.

## 13. Docker and Compose

- Project name `trip-planner`. One service `app`, one named volume `dados` holding the SQLite file at `/data/db.sqlite3`. The database never goes in the image or in Git.
- The `Dockerfile` has three stages: `base`, `dev` (adds test and lint tools) and `prod` (code baked in, runs gunicorn). Base image: `python:3.12-slim-trixie`.
- `compose.yaml` is production-like. `compose.override.yaml` is loaded automatically in development (bind mount, `runserver`, `DEBUG=1`) and forces the port to `127.0.0.1`.
- Published address and port come from `APP_BIND` (default `127.0.0.1`) and `APP_PORT` in `.env`. Exposing the app to the private network means setting `APP_BIND` to the machine's LAN IP and adding that host to `DJANGO_ALLOWED_HOSTS`. Do this only in production-like mode, never with `DEBUG` on. Docker-published ports bypass `ufw`, so the bind address is the real control.
- Never run `docker compose down -v` without explicit confirmation: it deletes the database volume.
- Images contain nothing machine-specific. Hostnames, IPs and secrets live in each machine's `.env`.

## 14. Security

- No secrets in code, commits, logs or examples. Use environment variables; `.env` is git-ignored and `.env.example` has no real values.
- Keep CSRF protection on. Data belongs to the shared family space: every view requires an authenticated member, and accounts are created by the admin.
- `DEBUG = False` and a strict `ALLOWED_HOSTS` outside local development.
- Until HTTPS exists, do not enable secure-cookie or SSL-redirect settings (login would break over HTTP).
- Never mark user input as safe in templates without sanitizing it.
- Validate all input on the server side.
- Add tests that unauthenticated users cannot read or change any data.

## 15. Ask before you do these

- Deleting data, volumes, migrations or files you did not create.
- Adding or upgrading a dependency.
- Changing the specification, the data model or a public behavior.
- Running commands that affect anything outside this repository.
- Any step you are unsure is reversible.

## 16. Git

Small, focused commits with imperative messages (for example `Add Makefile`). Never commit `.env`, database files or virtual environments. Do not rewrite shared history without explicit permission.

## 17. Skills and agent roles

Skills live in `.github/skills/<name>/SKILL.md` and agent roles in `.github/agents/<name>.agent.md`. Edit them there directly.

## 18. Definition of done

A change is done when all of these are true:

- `make check` passes.
- New or changed business rules in `servicos/` have unit tests, and every bug fix has a regression test.
- Money uses `Decimal` and no new `float` was added without `# allow-float: reason`.
- Models changed, and the migration is committed.
- User-facing text is in Brazilian Portuguese; code, comments and commits are in English.
- `AGENTS.md` (section 2) and `docs/project-files.md` reflect any file added or removed.
- The commit is small, has an imperative message and contains no secrets.
