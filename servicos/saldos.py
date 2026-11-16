from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from servicos.despesas import CARTAO_PRE_PAGO, DINHEIRO, ResultadoDaDespesa
from servicos.moeda import CASAS_COTACAO, CENTAVO

# RN-14: where the unallocated balance goes when the trip is completed.
CATEGORIA_DE_ENCERRAMENTO = {
    CARTAO_PRE_PAGO: "Outros gastos de cartão pré-pago",
    DINHEIRO: "Outros gastos com dinheiro",
}


@dataclass(frozen=True)
class EstadoDoSaldo:
    """What is left of one balance (same trip, type and currency), RN-17."""

    valor_restante: Decimal = Decimal(0)
    custo_restante: Decimal = Decimal(0)  # BRL, with the IOF already paid


def custo_medio(estado: EstadoDoSaldo) -> Decimal:
    """RN-22: BRL per unit. For display only; costs below are computed without this rounding."""
    if estado.valor_restante <= 0:
        raise ValueError("Não há saldo para calcular o custo médio.")
    return (estado.custo_restante / estado.valor_restante).quantize(
        CASAS_COTACAO, rounding=ROUND_HALF_UP
    )


def registrar_compra(estado: EstadoDoSaldo, valor: Decimal, custo_brl: Decimal) -> EstadoDoSaldo:
    """RN-22: the new average is (remaining cost + new cost) / (remaining + bought)."""
    if valor <= 0:
        raise ValueError("O valor comprado ou carregado precisa ser positivo.")
    if custo_brl < 0:
        raise ValueError("O custo em reais não pode ser negativo.")
    return EstadoDoSaldo(estado.valor_restante + valor, estado.custo_restante + custo_brl)


def custo_do_uso(estado: EstadoDoSaldo, valor: Decimal) -> Decimal:
    """RN-22: average cost times the amount spent, rounded once; no new IOF (RN-14)."""
    _validar_uso(estado, valor)
    if valor == estado.valor_restante:
        # Spending everything takes the exact remaining cost, so no cents are left behind.
        return estado.custo_restante
    return (estado.custo_restante * valor / estado.valor_restante).quantize(
        CENTAVO, rounding=ROUND_HALF_UP
    )


def registrar_uso(estado: EstadoDoSaldo, valor: Decimal) -> tuple[EstadoDoSaldo, Decimal]:
    """Returns the new state and the BRL cost of this use."""
    custo = custo_do_uso(estado, valor)
    return EstadoDoSaldo(estado.valor_restante - valor, estado.custo_restante - custo), custo


def calcular_despesa_com_saldo(estado: EstadoDoSaldo, valor: Decimal) -> ResultadoDaDespesa:
    """RN-14, RN-22: no new IOF. The stored rate is the average cost, for display only."""
    return ResultadoDaDespesa(
        cotacao=custo_medio(estado),
        valor_brl=custo_do_uso(estado, valor),
        taxa_iof=Decimal(0),
        valor_iof=Decimal(0),
    )


def disponivel(estado: EstadoDoSaldo, reservado: Decimal) -> Decimal:
    """RN-14: what can still be allocated after the planned costs already linked to the balance."""
    return max(estado.valor_restante - reservado, Decimal(0))


def categoria_de_encerramento(tipo: str) -> str:
    try:
        return CATEGORIA_DE_ENCERRAMENTO[tipo]
    except KeyError:
        raise ValueError("O saldo só existe em cartão pré-pago ou dinheiro.") from None


def _validar_uso(estado: EstadoDoSaldo, valor: Decimal) -> None:
    if valor <= 0:
        raise ValueError("O valor gasto do saldo precisa ser positivo.")
    if valor > estado.valor_restante:
        raise ValueError("O saldo não cobre esse valor.")
