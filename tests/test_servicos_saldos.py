from decimal import Decimal

import pytest

from servicos.saldos import (
    EstadoDoSaldo,
    calcular_despesa_com_saldo,
    categoria_de_encerramento,
    custo_do_uso,
    custo_medio,
    motivo_de_bloqueio_da_compra,
    recompor_saldo,
    registrar_compra,
    registrar_uso,
)


def _estado(valor, custo):
    return EstadoDoSaldo(Decimal(valor), Decimal(custo))


def test_first_purchase_sets_amount_and_cost():
    estado = registrar_compra(EstadoDoSaldo(), Decimal("100"), Decimal("505.50"))

    assert estado == _estado("100", "505.50")
    assert custo_medio(estado) == Decimal("5.05500000")


def test_second_purchase_recalculates_the_average_cost():
    estado = _estado("100", "500.00")

    estado = registrar_compra(estado, Decimal("100"), Decimal("600.00"))

    assert estado == _estado("200", "1100.00")
    assert custo_medio(estado) == Decimal("5.50000000")


def test_average_cost_uses_only_what_is_left_after_spending():
    estado, _ = registrar_uso(_estado("100", "500.00"), Decimal("40"))

    estado = registrar_compra(estado, Decimal("40"), Decimal("240.00"))

    assert estado == _estado("100", "540.00")


def test_use_costs_average_times_amount():
    estado, custo = registrar_uso(_estado("100", "505.50"), Decimal("20"))

    assert custo == Decimal("101.10")
    assert estado == _estado("80", "404.40")


def test_use_rounds_once_half_up():
    # 10.00 * 1 / 3 = 3.333...; 10.00 * 2 / 3 = 6.666...
    assert custo_do_uso(_estado("3", "10.00"), Decimal("1")) == Decimal("3.33")
    assert custo_do_uso(_estado("3", "10.00"), Decimal("2")) == Decimal("6.67")
    # 0.05 * 1 / 2 = 0.025 rounds half up
    assert custo_do_uso(_estado("2", "0.05"), Decimal("1")) == Decimal("0.03")


def test_spending_everything_takes_the_exact_remaining_cost():
    estado = _estado("3", "10.00")
    total = Decimal(0)
    for _ in range(3):
        estado, custo = registrar_uso(estado, Decimal("1"))
        total += custo

    assert estado == _estado("0", "0.00")
    assert total == Decimal("10.00")


def test_uses_never_leave_a_negative_cost():
    estado = _estado("7", "0.10")
    while estado.valor_restante > 0:
        estado, _ = registrar_uso(estado, Decimal("1"))
        assert estado.custo_restante >= 0


def test_decimal_amounts_with_different_places():
    estado, custo = registrar_uso(_estado("1000", "35.00"), Decimal("250.50"))

    assert custo == Decimal("8.77")
    assert estado == _estado("749.50", "26.23")


def test_use_above_the_balance_is_refused():
    with pytest.raises(ValueError, match="saldo"):
        custo_do_uso(_estado("10", "50.00"), Decimal("10.01"))


@pytest.mark.parametrize("valor", ["0", "-1"])
def test_use_must_be_positive(valor):
    with pytest.raises(ValueError, match="positivo"):
        custo_do_uso(_estado("10", "50.00"), Decimal(valor))


@pytest.mark.parametrize(("valor", "custo"), [("0", "10.00"), ("-5", "10.00"), ("10", "-0.01")])
def test_purchase_needs_positive_amount_and_non_negative_cost(valor, custo):
    with pytest.raises(ValueError):
        registrar_compra(EstadoDoSaldo(), Decimal(valor), Decimal(custo))


def test_average_cost_without_balance_is_refused():
    with pytest.raises(ValueError):
        custo_medio(EstadoDoSaldo())


def test_balance_paid_expense_uses_the_average_cost():
    resultado = calcular_despesa_com_saldo(_estado("100", "505.50"), Decimal("20"))

    assert resultado.valor_brl == Decimal("101.10")
    assert resultado.cotacao == Decimal("5.05500000")


def test_balance_paid_expense_above_the_balance_is_refused():
    with pytest.raises(ValueError, match="saldo"):
        calcular_despesa_com_saldo(_estado("10", "50.00"), Decimal("11"))


def test_closing_category_depends_on_the_balance_type():
    assert categoria_de_encerramento("cartao_pre_pago") == "Outros gastos de cartão pré-pago"
    assert categoria_de_encerramento("dinheiro") == "Outros gastos com dinheiro"


def test_closing_category_refuses_other_types():
    with pytest.raises(ValueError):
        categoria_de_encerramento("cartao_credito")


def test_rebuilding_a_balance_adds_up_its_purchases():
    estado = recompor_saldo(
        [(Decimal("100"), Decimal("505.50")), (Decimal("50"), Decimal("303.00"))]
    )

    assert estado == _estado("150", "808.50")


def test_rebuilding_a_balance_without_purchases_is_empty():
    assert recompor_saldo([]) == EstadoDoSaldo()


def test_purchase_can_change_while_nothing_was_spent():
    assert motivo_de_bloqueio_da_compra(encerrado=False, ha_uso=False) is None


def test_closed_balance_blocks_purchase_changes():
    assert "encerrado" in motivo_de_bloqueio_da_compra(encerrado=True, ha_uso=False)


def test_use_blocks_purchase_changes():
    assert "pagas com esse saldo" in motivo_de_bloqueio_da_compra(encerrado=False, ha_uso=True)
