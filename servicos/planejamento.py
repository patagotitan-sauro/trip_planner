from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol

from servicos.despesas import ComValorEmBrl, total_em_brl

MOVIMENTO_COMPRA = "compra"


class ComMovimento(ComValorEmBrl, Protocol):
    movimento_saldo: str
    saldo_id: int | None


def nao_alocado_por_saldo(despesas: Iterable[ComMovimento]) -> dict[int, Decimal]:
    """RN-14: per balance, the purchases' cost minus what expenses paid with it took out."""
    compradas: dict[int, Decimal] = defaultdict(Decimal)
    alocadas: dict[int, Decimal] = defaultdict(Decimal)
    for despesa in despesas:
        if despesa.saldo_id is None:
            continue
        custo = total_em_brl([despesa])
        if despesa.movimento_saldo == MOVIMENTO_COMPRA:
            compradas[despesa.saldo_id] += custo
        else:
            alocadas[despesa.saldo_id] += custo
    return {saldo: custo - alocadas[saldo] for saldo, custo in compradas.items()}


def total_da_viagem(despesas: Sequence[ComMovimento]) -> Decimal:
    """RN-14: expenses, plus each balance's purchase cost not yet allocated."""
    gastos = total_em_brl(d for d in despesas if d.movimento_saldo != MOVIMENTO_COMPRA)
    return gastos + sum(nao_alocado_por_saldo(despesas).values(), Decimal(0))


def totais_por_ano(itens: Iterable[tuple[date, Decimal]]) -> dict[int, Decimal]:
    """RN-23: sums per year of the trip's end date (`data` is that end date), newest year first."""
    por_ano: dict[int, Decimal] = {}
    for data_fim, total in itens:
        por_ano[data_fim.year] = por_ano.get(data_fim.year, Decimal(0)) + total
    return dict(sorted(por_ano.items(), reverse=True))
