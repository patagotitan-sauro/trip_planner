from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from servicos.moeda import MOEDA_CASA, converter_para_brl

CARTAO_CREDITO = "cartao_credito"
CARTAO_DEBITO = "cartao_debito"
CARTAO_PRE_PAGO = "cartao_pre_pago"
DINHEIRO = "dinheiro"
PIX = "pix"


@dataclass(frozen=True)
class ResultadoDaDespesa:
    cotacao: Decimal
    valor_brl: Decimal


class ComValorEmBrl(Protocol):
    valor_brl: Decimal | None


def moeda_estrangeira(moeda: str) -> bool:
    return moeda != MOEDA_CASA


def calcular_despesa(valor: Decimal, moeda: str, cotacao: Decimal | None) -> ResultadoDaDespesa:
    """Converts to BRL, frozen when the expense is recorded (RN-08)."""
    if valor < 0:
        raise ValueError("O valor não pode ser negativo.")
    if moeda_estrangeira(moeda):
        if cotacao is None:
            raise ValueError("Informe a cotação da moeda estrangeira.")
        taxa_de_conversao = cotacao
    else:
        taxa_de_conversao = Decimal(1)
    return ResultadoDaDespesa(
        cotacao=taxa_de_conversao, valor_brl=converter_para_brl(valor, taxa_de_conversao)
    )


def validar_forma_de_pagamento(
    moeda: str, forma_pagamento: str, com_saldo: bool = False
) -> str | None:
    """RN-13, RN-14: returns an error message, or None when the combination is allowed."""
    if com_saldo:
        if forma_pagamento not in (CARTAO_PRE_PAGO, DINHEIRO):
            return "Gasto pago com saldo usa cartão pré-pago ou dinheiro."
        return None
    if not moeda_estrangeira(moeda):
        return None
    if not forma_pagamento:
        return "Informe a forma de pagamento para gastos em moeda estrangeira."
    if forma_pagamento in (CARTAO_DEBITO, PIX):
        return "Cartão de débito e Pix só valem em reais."
    if forma_pagamento != CARTAO_CREDITO:
        return "Gasto em moeda estrangeira só pode ser pago no cartão de crédito, ou com saldo."
    return None


def total_em_brl(despesas: Iterable[ComValorEmBrl]) -> Decimal:
    """Sum of the converted amounts."""
    total = Decimal(0)
    for despesa in despesas:
        if despesa.valor_brl is None:
            raise ValueError("Despesa sem valor em BRL não pode entrar no total.")
        total += despesa.valor_brl
    return total
