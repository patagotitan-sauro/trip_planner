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
- [x] Login with Django auth; accounts created only by the admin.
- [x] Every view requires login (`LoginRequiredMiddleware`).
- [x] Base template in pt-BR (Pico CSS) and a placeholder home page.
- [x] Test: each URL without login redirects to login.
- Depends on: Phase 0.

## Phase 2: Trips (`viagens`)
- [x] List trips by state (stand-by, planning, completed grouped by year), with a national/international filter.
- [x] Create and edit a trip: name, dates, optional budget.
- [x] Destinations: country (default Brasil) and city, both required; the first one is asked when creating the trip, more come from an "Acrescentar novo destino" button on the trip page.
- [x] Itinerary by date, or by numbered day in stand-by (RN-18, RN-24): add, edit and remove activities on the trip page.
- [x] Use `classificar_viagem` (RN-02) for the national or international label.
- [x] Delete planning and stand-by trips, after a confirmation page (RF-09). Completed trips cannot be deleted.
- [x] Change a trip's state (RF-08): stand-by to planning (asks the dates), planning to stand-by, complete, reopen; each with a confirmation page. The itinerary is converted between dates and day numbers.
- Deferred by the owner: IOF rates in the trip form (RN-12) go to Phase 3.
- Depends on: Phase 1.

## Phase 3: Expenses (`despesas`)
- [x] Rules in `servicos/despesas.py`: IOF per RN-09 to RN-11, reusing `servicos/moeda.py`. Cash and prepaid purchases (RN-13) wait for Phase 4.
- [x] Create, edit and delete expenses per trip: category, currency, amount, planned or actual, optional activity link (RN-24, RN-25). IOF and BRL value are computed and stored on save; the trip's current IOF rates only apply to new or changed entries (RN-12).
- [x] List the expenses of a trip, planned and realized separately, with totals in BRL (IOF included and shown apart).
- [x] Each credit-card expense keeps its own rate (RN-08).
- [x] Tests: IOF amounts, rounding, 8-decimal rates.
- [x] IOF rates per trip in the trip form (RN-12), as percentages; blank keeps the current rate. Schema added in its own commit.
- Depends on: Phase 2. The rules can be written during Phase 2.

## Phase 4: Balances (`saldos`) - needs schema confirmation
- [ ] Register prepaid card and cash purchases.
- [ ] Allocate balances to planned costs or expenses (RN-14, RN-16, RN-17).
- [ ] Average cost per RN-22; close a trip with confirmation (RN-14).
- [ ] When completing a trip, also close the unallocated balances (RN-14); the completion screen already exists (RF-08).
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

## Backlog (deferred, no phase yet)
- [ ] Delete expenses and other posted data, in the screens that create them (RN-21).

## Out of scope for the first version (spec section 1)
Expense splitting, reservation checklists, charts and reports, per-category budgets, bank spread.
