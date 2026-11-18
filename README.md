# Trip Planner

A family web app to study possible trips and decide which one to take, manage the expenses of the chosen trip, and keep a history of completed trips with their costs. Small, personal use; the interface is in Brazilian Portuguese.

## Key features

- Trips in three states: stand-by (no dates), planning and completed (grouped by year), with a national/international label and filter.
- State changes with a confirmation page (stand-by to planning, complete, reopen); planning and stand-by trips can be deleted.
- Destinations (country and city) and a day-by-day itinerary (by date, or by numbered day in stand-by).
- Expenses per trip: create, edit and delete, planned and realized, by category, in any currency, optionally linked to an itinerary activity.
- IOF and the BRL value are computed and stored when an expense is recorded; IOF rates are set per trip.
- Expense list per trip with BRL totals, planned and realized separately.
- Prepaid card and cash balances per trip: register a purchase or load (and change or delete it while nothing was spent from it), pay or reserve expenses with a balance (counted at the average cost), and close leftover balances when completing the trip.
- Optional budget per trip, with the remaining value shown against the planned costs.
- Planning page: planned totals per year and the cancelable costs by deadline.
- History: realized total of each completed trip and of each year.
- Exchange-rate suggestion (Frankfurter) on the expense and balance purchase forms; the rate stays editable.
- Login only; accounts are created by the admin and all members share the same data.
- Backup and restore of the SQLite database.

Remaining work (see [docs/roadmap.md](docs/roadmap.md)): production configuration and operations, currency suggestion from the destination country, and deleting posted data that is still deferred.

## Technology stack

| Area | Choice |
|---|---|
| Language | Python 3.12 |
| Framework | Django 5.2 LTS, server-rendered templates |
| Database | SQLite (WAL mode) |
| UI | Pico CSS 2.1.1 (vendored) |
| Serving | gunicorn and WhiteNoise (production) |
| Packaging | Docker Compose, base image `python:3.12-slim-trixie` |
| Tests and lint | pytest, pytest-django, ruff |

## Architecture

Dependencies point one way: presentation, then services, then models and integrations.

| Layer | Where | Responsibility |
|---|---|---|
| Presentation | `apps/*/views.py`, `forms.py`, `templates/` | HTTP, forms, rendering. No business rules |
| Services | `servicos/` | Business rules in pure Python: money, conversion, IOF, balances, trip rules |
| Models | `apps/*/models.py` | Entities and persistence |
| Integrations | `servicos/integracoes/` | External APIs behind an interface |

## Getting started

Prerequisites: Docker with Compose, and `make`.

```bash
make init        # create .env from .env.example (never overwrites)
# edit .env: set DJANGO_SECRET_KEY, and DJANGO_DEBUG if needed
make up          # build and start (development, http://127.0.0.1:8085)
make superuser   # create an admin account
```

Environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Required; replace `change-me` |
| `DJANGO_DEBUG` | `1` enables debug mode; `0` by default |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts, for example `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins; empty by default |
| `APP_PORT` | Published port (`8085` in `.env.example`) |

`compose.yaml` also reads `APP_BIND` (default `127.0.0.1`) to choose the published address.

Common commands (`make help` lists all):

| Command | What it does |
|---|---|
| `make down` | Stop, keeping the data volume |
| `make logs` / `make shell` | Follow logs / open a shell in the container |
| `make migrations` / `make migrate` | Create / apply migrations |
| `make backup` / `make restore FILE=...` | Back up / restore the database |
| `make prod-up` | Production-like run, without the dev override |

Never run `docker compose down -v`: it deletes the database volume.

## Project structure

```
apps/        Django apps: contas (login), viagens, despesas, saldos, planejamento
config/      Django settings, URLs, WSGI/ASGI
servicos/    Business rules (pure Python) and integrations/
templates/   Base template
static/      Pico CSS and project styles
scripts/     Backup, restore and money-float check
tests/       pytest suite
docs/        Specification, roadmap, file guide
```

Details: [docs/project-files.md](docs/project-files.md).

The requirements and business rules are in [docs/especificacao.md](docs/especificacao.md). The implementation phases are tracked in [docs/roadmap.md](docs/roadmap.md).

## Development workflow

- Follow the phases in [docs/roadmap.md](docs/roadmap.md), one concern per small commit.
- Requirements and business rules (RN-xx, RF-xx) are in [docs/especificacao.md](docs/especificacao.md).
- Commits: English, imperative mood, title up to 50 characters, no prefix (see [.github/commit-instructions.md](.github/commit-instructions.md)).
- CI runs `make check` on every push to `main` and on pull requests ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Coding standards

- PEP 8 and type hints on new functions; ruff for lint and format.
- Money uses `Decimal` and `DecimalField`, never `float`. Rounding happens in one place.
- Views stay thin; business rules go in `servicos/`.
- User-facing text in Brazilian Portuguese; code, comments and commits in English.
- Every view requires an authenticated user; no secrets in code or commits.

The full guide is [AGENTS.md](AGENTS.md).

## Testing

```bash
make test    # pytest
make lint    # ruff check, ruff format --check, float-for-money check
make check   # lint, manage.py check, migrations check, then tests
```

Business rules in `servicos/` are unit tested without a database or HTTP. Tests are deterministic and make no real network calls.

## Contributing

1. Read [AGENTS.md](AGENTS.md) and the next open phase in [docs/roadmap.md](docs/roadmap.md).
2. Keep the change small and add tests (a regression test for every bug fix).
3. Run `make check` before committing.
4. Update `AGENTS.md` (section 2) and `docs/project-files.md` when files are added or removed.

## License

Apache License 2.0. See [LICENSE](LICENSE).
