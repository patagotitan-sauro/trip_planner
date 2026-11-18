from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from servicos import planejamento


@dataclass
class DespesaFalsa:
    valor_brl: Decimal | None
    movimento_saldo: str = ""
    saldo_id: int | None = None


def test_total_sums_the_expenses():
    despesas = [DespesaFalsa(Decimal("100.00")), DespesaFalsa(Decimal("50.50"))]

    assert planejamento.total_da_viagem(despesas) == Decimal("150.50")


def test_purchase_counts_as_unallocated_cost_until_it_is_used():
    compra = DespesaFalsa(Decimal("505.50"), "compra", saldo_id=1)

    assert planejamento.total_da_viagem([compra]) == Decimal("505.50")
    assert planejamento.nao_alocado_por_saldo([compra]) == {1: Decimal("505.50")}


def test_use_moves_its_amount_out_of_unallocated_without_double_counting():
    compra = DespesaFalsa(Decimal("500.00"), "compra", saldo_id=1)
    uso = DespesaFalsa(Decimal("200.00"), "uso", saldo_id=1)

    assert planejamento.nao_alocado_por_saldo([compra, uso]) == {1: Decimal("300.00")}
    assert planejamento.total_da_viagem([compra, uso]) == Decimal("500.00")


def test_closing_takes_the_remaining_unallocated_amount_into_the_total():
    compra = DespesaFalsa(Decimal("500.00"), "compra", saldo_id=1)
    uso = DespesaFalsa(Decimal("200.00"), "uso", saldo_id=1)
    encerramento = DespesaFalsa(Decimal("300.00"), "encerramento", saldo_id=1)

    assert planejamento.total_da_viagem([compra, uso, encerramento]) == Decimal("500.00")
    assert planejamento.nao_alocado_por_saldo([compra, uso, encerramento]) == {1: Decimal("0.00")}


def test_unallocated_is_kept_per_balance():
    compra_a = DespesaFalsa(Decimal("500.00"), "compra", saldo_id=1)
    compra_b = DespesaFalsa(Decimal("300.00"), "compra", saldo_id=2)
    uso_a = DespesaFalsa(Decimal("120.00"), "uso", saldo_id=1)

    assert planejamento.nao_alocado_por_saldo([compra_a, compra_b, uso_a]) == {
        1: Decimal("380.00"),
        2: Decimal("300.00"),
    }


def test_total_without_expenses_is_zero():
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
