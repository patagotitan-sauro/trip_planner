# Roadmap: trip planner (one phase per chat)

How to use: start each new chat with "Read docs/roadmap.md and AGENTS.md, then do the next open phase." Mark each phase [x] when its commits are done and `make check` passes. Update this file in the same chat.

Rules for every phase (from AGENTS.md):
- Business rules first in `servicos/` (pure Python, unit tests), then models and migrations, then thin views and pt-BR templates.
- Schema changes: outline the plan and wait for confirmation before creating files.
- Small commits, one concern each, imperative messages in English.
- End with `make check`, and say how to check the change in the browser.

## Done
- [x] Data layer: viagens and despesas models, IOF and conversion rules, classification, one-time import, backup and restore scripts.

## Scope change: only expenses (no planned/realized, no IOF, no budget)
Done out of sequence at the owner's request; it supersedes the items below that mention planned costs, IOF, the budget or cancelable costs. Those items stay as history.
- [x] Spec updated (`docs/especificacao.md`): one kind of record, "gasto"; RN-09 to RN-12, RN-15, RN-19, RN-20, RF-11, RF-15 and RF-18 removed (numbers are not reused); RN-13, RN-14, RN-16, RN-17, RN-22, RN-23 and the screen requirements reworded.
- [x] Rules in `servicos/`: no IOF, no `PLANEJADA`/`REALIZADA`, no budget remaining, no cancelable rules, no reservation of a balance. `total_da_viagem` counts each balance purchase once (RN-14).
- [x] Schema (confirmed): `Despesa` lost `situacao`, `taxa_iof`, `valor_iof`, `cancelavel`, `data_limite_cancelamento` and their constraints; `Viagem` lost `orcamento`, `aliquota_iof_credito` and `aliquota_iof_pre_pago_dinheiro`. Migrations `despesas` 0009 (data), `despesas` 0010 and `viagens` 0003. The data migration rebuilds each balance without IOF; a planned reservation on an open balance became a real use, on a closed balance it was deleted (the closing already held it).
- [x] Screens: one "Novo gasto" entry, one list with a single total, the trip total in every trip table, the planning page with the total spent per year; the budget, IOF rates and cancelable sections are gone.

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
- [x] Rules in `servicos/despesas.py`: IOF per RN-09 to RN-11, reusing `servicos/moeda.py`. Cash and prepaid purchases (RN-13) are in Phase 4.
- [x] Create, edit and delete expenses per trip: category, currency, amount, planned or actual, optional activity link (RN-24, RN-25). IOF and BRL value are computed and stored on save; the trip's current IOF rates only apply to new or changed entries (RN-12).
- [x] List the expenses of a trip, planned and realized separately, with totals in BRL (IOF included and shown apart).
- [x] Each credit-card expense keeps its own rate (RN-08).
- [x] Tests: IOF amounts, rounding, 8-decimal rates.
- [x] IOF rates per trip in the trip form (RN-12), as percentages; blank keeps the current rate. Schema added in its own commit.
- Depends on: Phase 2. The rules can be written during Phase 2.

## Phase 4: Balances (`saldos`)
- [x] Rules in `servicos/saldos.py`: average cost, purchase, use at average cost, available amount, closing category (RN-14, RN-17, RN-22). Balance payment accepted in `servicos/despesas.py`.
- [x] Schema (confirmed): `Saldo` per trip, type and currency; `Despesa.saldo` and `movimento_saldo`; the two "Outros gastos..." categories. Accounting: the purchase or load is a realized cost titled "Compra de moeda estrangeira não alocada" until it is used or reserved, expenses paid with a balance count at the average cost, the leftover is posted at closing (RN-14).
- [x] Register prepaid card and cash purchases (RF-13, RN-13): form, balances list on the trip page, IOF at the trip's rate.
- [x] Allocate balances to planned costs or expenses (RF-14, RF-15, RN-14, RN-16, RN-17): the expense form asks whether to pay with the balance; a planned cost reserves it.
- [x] When completing a trip, show the unallocated balances and close them into the "Outros gastos..." categories after confirmation (RF-16, RN-14); the completion screen already exists (RF-08). Everything left in a balance is closed, including amounts still reserved by planned costs.
- Decided for this phase: expenses linked to a balance (purchases, uses, closings) cannot be edited or deleted until the RN-21 backlog item; reopening a trip does not reopen closed balances. Purchases became editable and deletable afterwards (see the backlog).
- Depends on: Phase 3.

## Phase 5: Planning and history
- [x] Rules in `servicos/planejamento.py`: totals per year, budget remaining, deadline order and validation, trip total that counts each purchase once, as unallocated balance or as allocated spending (RN-06, RN-14, RN-19, RN-20, RN-23).
- [x] Planned totals per year (RN-23, RF-17): the "Planejamento" page (new app `planejamento`, no models) lists trips in planning by end-date year, with the planned total of each trip and of each year. Stand-by trips are left out.
- [x] Budget remaining (RN-19, RF-17): budget minus planned costs only, shown on the planning page, the trip page and the trip card for trips with a budget (not completed ones); over budget is flagged.
- [x] Cancelable expenses with a deadline (RN-20, RF-10, RF-18): `Despesa.cancelavel` and `data_limite_cancelamento` (schema confirmed, migration 0007), the checkbox and date in the expense form, and the list ordered by deadline on the planning page, with expired deadlines marked. Marking a cost as an expense clears the mark.
- [x] History totals for completed trips (RN-06, RN-23, RF-19): realized total on each completed trip and per year on the trips list (follows the national/international filter).
- Depends on: Phase 3.

## Phase 6: Exchange-rate API (`servicos/integracoes/`)
- [x] Protocol (interface) plus a Frankfurter client: `servicos/integracoes/cotacao.py` (`ProvedorDeCotacao`, `CotacaoSugerida`, `CotacaoIndisponivel`), `servicos/integracoes/frankfurter.py` (standard library only, https only, 5 s timeout) and the rule in `servicos/cotacao.py` (the expense date's rate; the latest when there is no date or it is in the future).
- [x] The form suggests the rate; the user can edit it (RN-08): a "Sugerir cotação" button on the expense form and on the balance purchase form reloads the form with the rate filled in; nothing is saved until the user saves. No JavaScript.
- [x] Tests mock the network; no real calls in tests (an autouse fixture blocks `urlopen`).
- Not done: suggesting the currency from the destination country (RN-07, RF-11); no rate cache.

## Phase 7: Production
- [ ] `.env` on the main computer: DEBUG off, ALLOWED_HOSTS set.
- [ ] `make prod-up` on the main computer.
- [ ] Backup scheduled (cron) and copied off the machine.
- [ ] Restore tested once.
- [ ] CI runs `make check` on each push.
- [ ] The production container can reach `api.frankfurter.dev` over HTTPS (rate suggestion).

## Backlog (deferred, no phase yet)
- [x] Trip list UX (done out of sequence, branch `ux-improvements`): a compact table with one row per trip (name, start, end, total; newest first; "Editar" only for trips in planning); stand-by trips moved to their own page ("Viagens em stand-by", with the type filter) and a "Custo global" (realized plus planned, purchases and loads not counted twice, RN-14) on each planning or stand-by trip. The yearly totals (RN-23) are unchanged.
- [x] Change or delete a balance purchase or load (RN-21): from the expense list; amount, rate and date can change (type and currency cannot, and the IOF rate stays as recorded); allowed only while the balance is open and nothing was spent from it, and not below what planned costs reserve. Deleting the only purchase removes the balance.
- [x] Unallocated balance as a realized cost (RN-14): a purchase or load is a realized cost titled "Compra de moeda estrangeira não alocada"; a use or a planned reservation takes its BRL value out of that line, so the total (realized plus planned) counts each amount once. The expense list shows the unallocated amount. Existing purchase rows were renamed by migration `0008` (data only).
- [ ] Delete expenses and other posted data, in the screens that create them (RN-21): still open for balance uses and closings.

## Out of scope for the first version (spec section 1)
Expense splitting, reservation checklists, charts and reports, per-category budgets, bank spread.
