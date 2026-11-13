# Roadmap: trip planner (one phase per chat)

How to use: start each new chat with "Read docs/roadmap.md and AGENTS.md, then do the next open phase." Mark each phase [x] when its commits are done and `make check` passes. Update this file in the same chat.

Rules for every phase (from AGENTS.md):
- Business rules first in `servicos/` (pure Python, unit tests), then models and migrations, then thin views and pt-BR templates.
- Schema changes: outline the plan and wait for confirmation before creating files.
- Small commits, one concern each, imperative messages in English.
- End with `make check`, and say how to check the change in the browser.

## Done
- [x] Data layer: viagens and despesas models, IOF and conversion rules, classification, one-time import, backup and restore scripts.

## Phase 0: Confirm (no code)
- [x] Write the RF-xx screen requirements in docs/especificacao.md (section 7; owner to review).
- [x] `contas` app: option A, login only; balances in `saldos`.
- [x] Japão: stand-by, country only (no city), as the import already does.
- [x] Trip names: keep the old destination text.

## Phase 1: Access (new app `contas`)
- [ ] Login with Django auth; accounts created only by the admin.
- [ ] Every view requires login.
- [ ] Base template in pt-BR.
- [ ] Test: each URL without login redirects to login.
- Depends on: Phase 0.

## Phase 2: Trips (`viagens`)
- [ ] List trips by state (stand-by, planning, completed grouped by year).
- [ ] Create and edit a trip: name, dates, optional budget.
- [ ] Destinations: country (django-countries select) and optional city.
- [ ] Itinerary by date, or by numbered day in stand-by (RN-18, RN-24).
- [ ] Use `classificar_viagem` (RN-02) for the national or international label.
- Depends on: Phase 1.

## Phase 3: Expenses (`despesas`)
- [ ] Rules in `servicos/`: IOF per RN-09 to RN-13, reusing `servicos/moeda.py`.
- [ ] Create and list expenses per trip: category, currency, amount, planned or actual, optional activity link (RN-24, RN-25).
- [ ] Each credit-card expense keeps its own rate (RN-08).
- [ ] Tests: IOF amounts, rounding, 8-decimal rates.
- Depends on: Phase 2. The rules can be written during Phase 2.

## Phase 4: Balances (`saldos`) - needs schema confirmation
- [ ] Register prepaid card and cash purchases.
- [ ] Allocate balances to planned costs or expenses (RN-14, RN-16, RN-17).
- [ ] Average cost per RN-22; close a trip with confirmation (RN-14).
- Depends on: Phase 3.

## Phase 5: Planning and history
- [ ] Planned totals per year (RN-23).
- [ ] Budget remaining (RN-19).
- [ ] Cancelable expenses with a deadline (RN-20).
- [ ] History totals for completed trips (RN-06).
- Depends on: Phase 3.

## Phase 6: Exchange-rate API (`servicos/integracoes/`)
- [ ] Protocol (interface) plus a Frankfurter client.
- [ ] The form suggests the rate; the user can edit it (RN-08).
- [ ] Tests mock the network; no real calls in tests.
- Can run in parallel with Phases 2 and 3.

## Phase 7: Production
- [ ] `.env` on the main computer: DEBUG off, ALLOWED_HOSTS set.
- [ ] `make prod-up` on the main computer.
- [ ] Backup scheduled (cron) and copied off the machine.
- [ ] Restore tested once.
- [ ] CI runs `make check` on each push.

## Out of scope for the first version (spec section 1)
Expense splitting, reservation checklists, charts and reports, per-category budgets, bank spread.
