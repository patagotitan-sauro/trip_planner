from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from servicos.moeda import CENTAVO, MOEDA_CASA, converter_para_brl

CARTAO_CREDITO = "cartao_credito"
CARTAO_DEBITO = "cartao_debito"
CARTAO_PRE_PAGO = "cartao_pre_pago"
DINHEIRO = "dinheiro"
PIX = "pix"

PLANEJADA = "planejada"
REALIZADA = "realizada"

# RN-10: default rates; each trip keeps its own copy (RN-12).
ALIQUOTA_CREDITO_PADRAO = Decimal("0.035")
ALIQUOTA_PRE_PAGO_DINHEIRO_PADRAO = Decimal("0.011")


@dataclass(frozen=True)
class ResultadoDaDespesa:
    cotacao: Decimal
    valor_brl: Decimal
    taxa_iof: Decimal
    valor_iof: Decimal

    @property
    def total_brl(self) -> Decimal:
        return self.valor_brl + self.valor_iof


class ComValoresEmBrl(Protocol):
    valor_brl: Decimal | None
    valor_iof: Decimal


def moeda_estrangeira(moeda: str) -> bool:
    return moeda != MOEDA_CASA


def aliquota_do_iof(
    forma_pagamento: str,
    moeda: str,
    aliquota_credito: Decimal,
    aliquota_pre_pago_dinheiro: Decimal,
) -> Decimal:
    """RN-09, RN-10: IOF only on foreign currency; the rate depends on the payment method."""
    if not moeda_estrangeira(moeda):
        return Decimal(0)
    if forma_pagamento == CARTAO_CREDITO:
        return aliquota_credito
    if forma_pagamento in (CARTAO_PRE_PAGO, DINHEIRO):
        return aliquota_pre_pago_dinheiro
    raise ValueError("Informe uma forma de pagamento com IOF para a moeda estrangeira.")


def calcular_iof(valor_brl: Decimal, aliquota: Decimal) -> Decimal:
    """RN-11: rounded once, half up, to cents."""
    return (valor_brl * aliquota).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def calcular_despesa(
    valor: Decimal,
    moeda: str,
    cotacao: Decimal | None,
    forma_pagamento: str,
    aliquota_credito: Decimal,
    aliquota_pre_pago_dinheiro: Decimal,
    taxa_iof_gravada: Decimal | None = None,
) -> ResultadoDaDespesa:
    """Converts to BRL and computes the IOF, all frozen when the expense is recorded.

    RN-12: `taxa_iof_gravada` is the rate already stored on an unchanged expense; it wins over
    the trip's current rates, which only apply to new entries.
    """
    if valor < 0:
        raise ValueError("O valor não pode ser negativo.")
    if moeda_estrangeira(moeda):
        if cotacao is None:
            raise ValueError("Informe a cotação da moeda estrangeira.")
        taxa_de_conversao = cotacao
    else:
        taxa_de_conversao = Decimal(1)

    aliquota = aliquota_do_iof(forma_pagamento, moeda, aliquota_credito, aliquota_pre_pago_dinheiro)
    if taxa_iof_gravada is not None and moeda_estrangeira(moeda):
        aliquota = taxa_iof_gravada
    valor_brl = converter_para_brl(valor, taxa_de_conversao)
    return ResultadoDaDespesa(
        cotacao=taxa_de_conversao,
        valor_brl=valor_brl,
        taxa_iof=aliquota,
        valor_iof=calcular_iof(valor_brl, aliquota),
    )


def validar_forma_de_pagamento(situacao: str, moeda: str, forma_pagamento: str) -> str | None:
    """RN-10, RN-13: returns an error message, or None when the combination is allowed."""
    if not moeda_estrangeira(moeda):
        return None
    if not forma_pagamento:
        return "Informe a forma de pagamento para despesas em moeda estrangeira."
    if forma_pagamento in (CARTAO_DEBITO, PIX):
        return "Cartão de débito e Pix só valem em reais."
    if situacao == REALIZADA and forma_pagamento != CARTAO_CREDITO:
        return "Despesa realizada em moeda estrangeira só pode ser paga no cartão de crédito."
    return None


def total_em_brl(despesas: Iterable[ComValoresEmBrl]) -> Decimal:
    """Sum of converted amounts plus IOF."""
    total = Decimal(0)
    for despesa in despesas:
        if despesa.valor_brl is None:
            raise ValueError("Despesa sem valor em BRL não pode entrar no total.")
        total += despesa.valor_brl + despesa.valor_iof
    return total
