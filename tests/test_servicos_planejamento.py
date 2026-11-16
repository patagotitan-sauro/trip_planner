from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from servicos import planejamento


@dataclass
class DespesaFalsa:
    valor_brl: Decimal | None
    valor_iof: Decimal = Decimal(0)
    movimento_saldo: str = ""


@dataclass
class ItemFalso:
    nome: str
    data_limite_cancelamento: date | None = None


def test_trip_total_sums_amount_and_iof():
    despesas = [
        DespesaFalsa(Decimal("100.00"), Decimal("3.50")),
        DespesaFalsa(Decimal("50.00")),
    ]

    assert planejamento.total_da_viagem(despesas) == Decimal("153.50")


def test_trip_total_leaves_out_purchases_but_keeps_uses_and_closings():
    compra = DespesaFalsa(Decimal("500.00"), Decimal("5.50"), "compra")
    uso = DespesaFalsa(Decimal("200.00"), movimento_saldo="uso")
    encerramento = DespesaFalsa(Decimal("300.00"), movimento_saldo="encerramento")

    assert planejamento.total_da_viagem([compra, uso, encerramento]) == Decimal("500.00")


def test_trip_total_without_expenses_is_zero():
    assert planejamento.total_da_viagem([]) == Decimal(0)


def test_totals_per_year_sum_by_end_year_newest_first():
    itens = [
        (date(2025, 1, 10), Decimal("100.00")),
        (date(2026, 3, 1), Decimal("50.00")),
        (date(2025, 12, 31), Decimal("25.50")),
    ]

    totais = planejamento.totais_por_ano(itens)

    assert list(totais) == [2026, 2025]
    assert totais == {2026: Decimal("50.00"), 2025: Decimal("125.50")}


def test_totals_per_year_without_trips_is_empty():
    assert planejamento.totais_por_ano([]) == {}


def test_remaining_is_budget_minus_planned_total():
    assert planejamento.valor_restante(Decimal("1000.00"), Decimal("350.25")) == Decimal("649.75")


def test_remaining_is_negative_when_over_budget():
    assert planejamento.valor_restante(Decimal("1000.00"), Decimal("1200.00")) == Decimal("-200.00")


def test_remaining_with_zero_budget_is_minus_the_planned_total():
    assert planejamento.valor_restante(Decimal("0"), Decimal("10.00")) == Decimal("-10.00")


def test_remaining_without_budget_is_none():
    assert planejamento.valor_restante(None, Decimal("350.25")) is None


def test_cancelable_planned_cost_with_deadline_is_valid():
    assert planejamento.validar_cancelamento("planejada", True, date(2027, 1, 5)) == {}


def test_not_cancelable_without_deadline_is_valid():
    assert planejamento.validar_cancelamento("realizada", False, None) == {}


def test_cancelable_requires_a_deadline():
    erros = planejamento.validar_cancelamento("planejada", True, None)

    assert list(erros) == ["data_limite_cancelamento"]


def test_realized_expense_cannot_be_cancelable():
    erros = planejamento.validar_cancelamento("realizada", True, date(2027, 1, 5))

    assert list(erros) == ["cancelavel"]


def test_deadline_without_the_cancelable_mark_is_rejected():
    erros = planejamento.validar_cancelamento("planejada", False, date(2027, 1, 5))

    assert list(erros) == ["data_limite_cancelamento"]


@pytest.mark.parametrize(
    ("limite", "vencido"),
    [
        (date(2026, 11, 15), True),
        (date(2026, 11, 16), False),
        (date(2026, 11, 17), False),
    ],
)
def test_deadline_is_expired_only_after_its_day(limite, vencido):
    assert planejamento.prazo_vencido(limite, date(2026, 11, 16)) is vencido


def test_sorts_by_earliest_deadline_and_drops_items_without_one():
    tarde = ItemFalso("hotel", date(2027, 2, 1))
    cedo = ItemFalso("voo", date(2026, 12, 1))
    sem_prazo = ItemFalso("passeio")

    assert planejamento.ordenar_por_prazo([tarde, sem_prazo, cedo]) == [cedo, tarde]
