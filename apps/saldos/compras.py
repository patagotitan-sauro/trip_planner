from django.db import transaction

from apps.despesas.models import Despesa, MovimentoSaldo
from servicos.saldos import motivo_de_bloqueio_da_compra, recompor_saldo

from .models import Saldo


def _compras_do_saldo(saldo: Saldo):
    return saldo.despesas.filter(movimento_saldo=MovimentoSaldo.COMPRA)


def motivo_de_bloqueio(compra: Despesa) -> str | None:
    """RN-21: why the purchase can be neither changed nor deleted, or None."""
    saldo = compra.saldo
    return motivo_de_bloqueio_da_compra(
        encerrado=saldo.encerrado,
        ha_uso=saldo.despesas.filter(movimento_saldo=MovimentoSaldo.USO).exists(),
    )


def refazer_saldo(saldo: Saldo) -> None:
    """The balance is only its purchases while nothing was spent, so it is rebuilt from them."""
    estado = recompor_saldo(
        (compra.valor_original, compra.valor_brl) for compra in _compras_do_saldo(saldo)
    )
    saldo.valor_restante, saldo.custo_restante = estado.valor_restante, estado.custo_restante
    saldo.save(update_fields=["valor_restante", "custo_restante"])


@transaction.atomic
def excluir_compra(compra: Despesa) -> None:
    saldo = compra.saldo
    compra.delete()
    if saldo.despesas.exists():
        refazer_saldo(saldo)
    else:
        saldo.delete()
