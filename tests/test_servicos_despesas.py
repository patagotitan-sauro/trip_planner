from dataclasses import dataclass
from decimal import Decimal

import pytest

from servicos import despesas


def _calcular(valor, moeda="USD", cotacao="5"):
    return despesas.calcular_despesa(
        Decimal(valor), moeda, None if cotacao is None else Decimal(cotacao)
    )


def test_foreign_currency_is_converted_at_the_given_rate():
    resultado = _calcular("100.00", cotacao="5")

    assert resultado.cotacao == Decimal("5")
    assert resultado.valor_brl == Decimal("500.00")


def test_brl_expense_keeps_rate_one():
    resultado = _calcular("250.00", moeda="BRL", cotacao=None)

    assert resultado.cotacao == Decimal(1)
    assert resultado.valor_brl == Decimal("250.00")


def test_brl_expense_ignores_a_given_rate():
    assert _calcular("10.00", moeda="BRL", cotacao="99").valor_brl == Decimal("10.00")


def test_zero_amount_gives_zero():
    assert _calcular("0.00").valor_brl == Decimal("0.00")


def test_negative_amount_is_rejected():
    with pytest.raises(ValueError, match="negativo"):
        _calcular("-1.00")


def test_foreign_currency_without_rate_is_rejected():
    with pytest.raises(ValueError, match="cotação"):
        _calcular("10.00", cotacao=None)


def test_rate_with_eight_decimals_is_used_without_early_rounding():
    resultado = _calcular("100.00", cotacao="5.12345678")

    assert resultado.valor_brl == Decimal("512.35")
    assert resultado.cotacao == Decimal("5.12345678")


def test_currency_without_decimal_places_converts_and_rounds_to_cents():
    # 1000 JPY at 0.03512345 BRL per yen.
    assert _calcular("1000", moeda="JPY", cotacao="0.03512345").valor_brl == Decimal("35.12")


@pytest.mark.parametrize(
    ("moeda", "forma", "erro"),
    [
        ("BRL", "", False),
        ("BRL", "pix", False),
        ("USD", "cartao_credito", False),
        ("USD", "dinheiro", True),
        ("USD", "cartao_pre_pago", True),
        ("USD", "pix", True),
        ("USD", "cartao_debito", True),
        ("USD", "", True),
    ],
)
def test_payment_method_rules_by_currency(moeda, forma, erro):
    mensagem = despesas.validar_forma_de_pagamento(moeda, forma)

    assert (mensagem is not None) is erro


@pytest.mark.parametrize("forma", ["cartao_pre_pago", "dinheiro"])
def test_balance_payment_is_allowed_in_foreign_currency(forma):
    assert despesas.validar_forma_de_pagamento("USD", forma, com_saldo=True) is None


@pytest.mark.parametrize("forma", ["cartao_credito", "cartao_debito", "pix", ""])
def test_balance_payment_refuses_other_payment_methods(forma):
    assert despesas.validar_forma_de_pagamento("USD", forma, com_saldo=True)


@dataclass
class DespesaFalsa:
    valor_brl: Decimal | None


def test_total_adds_converted_amounts():
    itens = [DespesaFalsa(Decimal("100.00")), DespesaFalsa(Decimal("0.01"))]

    assert despesas.total_em_brl(itens) == Decimal("100.01")


def test_total_of_nothing_is_zero():
    assert despesas.total_em_brl([]) == Decimal(0)


def test_total_rejects_an_expense_without_brl_amount():
    with pytest.raises(ValueError, match="sem valor em BRL"):
        despesas.total_em_brl([DespesaFalsa(None)])
