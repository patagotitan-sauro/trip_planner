from dataclasses import dataclass
from decimal import Decimal

import pytest

from servicos import despesas
from servicos.despesas import ALIQUOTA_CREDITO_PADRAO as CREDITO
from servicos.despesas import ALIQUOTA_PRE_PAGO_DINHEIRO_PADRAO as PRE_PAGO


def _calcular(valor, moeda="USD", cotacao="5", forma="cartao_credito"):
    return despesas.calcular_despesa(
        Decimal(valor),
        moeda,
        None if cotacao is None else Decimal(cotacao),
        forma,
        CREDITO,
        PRE_PAGO,
    )


def test_default_rates_follow_rn_10():
    assert CREDITO == Decimal("0.035")
    assert PRE_PAGO == Decimal("0.011")


def test_credit_card_in_foreign_currency_pays_3_5_percent_iof():
    resultado = _calcular("100.00", cotacao="5")

    assert resultado.valor_brl == Decimal("500.00")
    assert resultado.taxa_iof == Decimal("0.035")
    assert resultado.valor_iof == Decimal("17.50")
    assert resultado.total_brl == Decimal("517.50")


@pytest.mark.parametrize("forma", ["cartao_pre_pago", "dinheiro"])
def test_prepaid_and_cash_pay_1_1_percent_iof(forma):
    resultado = _calcular("100.00", cotacao="5", forma=forma)

    assert resultado.taxa_iof == Decimal("0.011")
    assert resultado.valor_iof == Decimal("5.50")


@pytest.mark.parametrize("forma", ["cartao_credito", "cartao_debito", "pix", "dinheiro", ""])
def test_brl_expense_never_has_iof_and_keeps_rate_one(forma):
    resultado = _calcular("250.00", moeda="BRL", cotacao=None, forma=forma)

    assert resultado.cotacao == Decimal(1)
    assert resultado.valor_brl == Decimal("250.00")
    assert resultado.valor_iof == Decimal("0.00")
    assert resultado.taxa_iof == Decimal(0)


def test_brl_expense_ignores_a_given_rate():
    assert _calcular("10.00", moeda="BRL", cotacao="99").valor_brl == Decimal("10.00")


def test_zero_amount_gives_zero_everything():
    resultado = _calcular("0.00")

    assert (resultado.valor_brl, resultado.valor_iof, resultado.total_brl) == (
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )


def test_negative_amount_is_rejected():
    with pytest.raises(ValueError, match="negativo"):
        _calcular("-1.00")


def test_foreign_currency_without_rate_is_rejected():
    with pytest.raises(ValueError, match="cotação"):
        _calcular("10.00", cotacao=None)


def test_foreign_currency_without_payment_method_is_rejected():
    with pytest.raises(ValueError, match="forma de pagamento"):
        _calcular("10.00", forma="")


@pytest.mark.parametrize("forma", ["cartao_debito", "pix"])
def test_debit_and_pix_have_no_iof_rate_for_foreign_currency(forma):
    with pytest.raises(ValueError, match="forma de pagamento"):
        _calcular("10.00", forma=forma)


def test_iof_is_rounded_half_up_once():
    assert despesas.calcular_iof(Decimal("0.50"), Decimal("0.035")) == Decimal("0.02")
    assert despesas.calcular_iof(Decimal("0.10"), Decimal("0.011")) == Decimal("0.00")
    assert despesas.calcular_iof(Decimal("1.50"), Decimal("0.011")) == Decimal("0.02")


def test_rate_with_eight_decimals_is_used_without_early_rounding():
    resultado = _calcular("100.00", cotacao="5.12345678")

    assert resultado.valor_brl == Decimal("512.35")
    assert resultado.cotacao == Decimal("5.12345678")
    assert resultado.valor_iof == Decimal("17.93")


def test_currency_without_decimal_places_converts_and_rounds_to_cents():
    # 1000 JPY at 0.03512345 BRL per yen.
    resultado = _calcular("1000", moeda="JPY", cotacao="0.03512345")

    assert resultado.valor_brl == Decimal("35.12")
    assert resultado.valor_iof == Decimal("1.23")


def test_iof_is_computed_on_the_rounded_brl_amount():
    # 33.33 * 0.03333333 = 1.1110998... -> 1.11 BRL; IOF 3.5% of 1.11 = 0.03885 -> 0.04
    resultado = _calcular("33.33", cotacao="0.03333333")

    assert resultado.valor_brl == Decimal("1.11")
    assert resultado.valor_iof == Decimal("0.04")


def test_custom_trip_rates_are_applied():
    resultado = despesas.calcular_despesa(
        Decimal("100.00"), "EUR", Decimal("6"), "cartao_credito", Decimal("0.04"), PRE_PAGO
    )

    assert resultado.valor_iof == Decimal("24.00")


@pytest.mark.parametrize(
    ("situacao", "moeda", "forma", "erro"),
    [
        ("realizada", "BRL", "", False),
        ("realizada", "BRL", "pix", False),
        ("planejada", "BRL", "", False),
        ("realizada", "USD", "cartao_credito", False),
        ("planejada", "USD", "cartao_credito", False),
        ("planejada", "USD", "dinheiro", False),
        ("planejada", "USD", "cartao_pre_pago", False),
        ("realizada", "USD", "dinheiro", True),
        ("realizada", "USD", "cartao_pre_pago", True),
        ("planejada", "USD", "pix", True),
        ("planejada", "USD", "cartao_debito", True),
        ("planejada", "USD", "", True),
        ("realizada", "USD", "", True),
    ],
)
def test_payment_method_rules_by_currency_and_situation(situacao, moeda, forma, erro):
    mensagem = despesas.validar_forma_de_pagamento(situacao, moeda, forma)

    assert (mensagem is not None) is erro


@dataclass
class DespesaFalsa:
    valor_brl: Decimal | None
    valor_iof: Decimal


def test_total_adds_converted_amounts_and_iof():
    itens = [
        DespesaFalsa(Decimal("100.00"), Decimal("3.50")),
        DespesaFalsa(Decimal("0.01"), Decimal("0.00")),
    ]

    assert despesas.total_em_brl(itens) == Decimal("103.51")


def test_total_of_nothing_is_zero():
    assert despesas.total_em_brl([]) == Decimal(0)


def test_iof_total_adds_only_the_iof():
    itens = [
        DespesaFalsa(Decimal("100.00"), Decimal("3.50")),
        DespesaFalsa(Decimal("10.00"), Decimal("0.11")),
    ]

    assert despesas.total_iof(itens) == Decimal("3.61")
    assert despesas.total_iof([]) == Decimal(0)


def test_total_rejects_an_expense_without_brl_amount():
    with pytest.raises(ValueError, match="sem valor em BRL"):
        despesas.total_em_brl([DespesaFalsa(None, Decimal("0.00"))])


def test_stored_rate_wins_over_the_trip_rates_for_an_unchanged_expense():
    resultado = despesas.calcular_despesa(
        Decimal("100.00"),
        "USD",
        Decimal("5"),
        "cartao_credito",
        Decimal("0.05"),
        PRE_PAGO,
        taxa_iof_gravada=Decimal("0.035"),
    )

    assert resultado.taxa_iof == Decimal("0.035")
    assert resultado.valor_iof == Decimal("17.50")


def test_stored_rate_is_ignored_for_brl():
    resultado = despesas.calcular_despesa(
        Decimal("100.00"), "BRL", None, "pix", CREDITO, PRE_PAGO, taxa_iof_gravada=Decimal("0.035")
    )

    assert (resultado.taxa_iof, resultado.valor_iof) == (Decimal(0), Decimal("0.00"))
