from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Protocol

from servicos.despesas import PLANEJADA, ComValoresEmBrl, total_em_brl

MOVIMENTO_COMPRA = "compra"


class ComMovimento(ComValoresEmBrl, Protocol):
    movimento_saldo: str


class ComPrazo(Protocol):
    data_limite_cancelamento: date | None


def contadas_no_total[T: ComMovimento](despesas: Iterable[T]) -> list[T]:
    """RN-14: the cost of a purchase or load is already in the balance, so it is not summed."""
    return [d for d in despesas if d.movimento_saldo != MOVIMENTO_COMPRA]


def total_da_viagem(despesas: Iterable[ComMovimento]) -> Decimal:
    """RN-06: BRL total (IOF included) of the entries that count."""
    return total_em_brl(contadas_no_total(despesas))


def totais_por_ano(itens: Iterable[tuple[date, Decimal]]) -> dict[int, Decimal]:
    """RN-23: sums per year of the trip's end date (`data` is that end date), newest year first."""
    por_ano: dict[int, Decimal] = {}
    for data_fim, total in itens:
        por_ano[data_fim.year] = por_ano.get(data_fim.year, Decimal(0)) + total
    return dict(sorted(por_ano.items(), reverse=True))


def valor_restante(orcamento: Decimal | None, total_planejado: Decimal) -> Decimal | None:
    """RN-19: no budget, nothing to show. Negative means the plan is over budget."""
    if orcamento is None:
        return None
    return orcamento - total_planejado


def validar_cancelamento(
    situacao: str, cancelavel: bool, data_limite: date | None
) -> dict[str, str]:
    """RN-20: only a planned cost can be cancelable, and it needs a deadline."""
    erros: dict[str, str] = {}
    if cancelavel and situacao != PLANEJADA:
        erros["cancelavel"] = "Só um custo planejado pode ser marcado como cancelável."
    elif cancelavel and data_limite is None:
        erros["data_limite_cancelamento"] = "Informe a data limite de cancelamento."
    elif not cancelavel and data_limite is not None:
        erros["data_limite_cancelamento"] = "A data limite só vale para custo cancelável."
    return erros


def prazo_vencido(data_limite: date, hoje: date) -> bool:
    """The deadline day itself is still valid."""
    return data_limite < hoje


def ordenar_por_prazo[T: ComPrazo](itens: Iterable[T]) -> list[T]:
    """RN-20: earliest deadline first; items without a deadline are not cancelable."""
    com_prazo = [i for i in itens if i.data_limite_cancelamento is not None]
    return sorted(com_prazo, key=lambda i: i.data_limite_cancelamento)
