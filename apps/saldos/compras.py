from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.despesas.models import Despesa, MovimentoSaldo, SituacaoDespesa
from servicos.saldos import motivo_de_bloqueio_da_compra, recompor_saldo

from .models import Saldo


def _custo_em_brl(compra: Despesa) -> Decimal:
    return compra.valor_brl + compra.valor_iof


def valores_atuais(compra: Despesa) -> tuple[Decimal, Decimal]:
    return compra.valor_original, _custo_em_brl(compra)


def _compras_do_saldo(saldo: Saldo):
    return saldo.despesas.filter(movimento_saldo=MovimentoSaldo.COMPRA)


def motivo_de_bloqueio(compra: Despesa, nova: tuple[Decimal, Decimal] | None) -> str | None:
    """RN-21: why the purchase cannot take `nova` (amount, BRL cost); None means deleting it."""
    saldo = compra.saldo
    restantes = [
        (outra.valor_original, _custo_em_brl(outra))
        for outra in _compras_do_saldo(saldo).exclude(pk=compra.pk)
    ]
    if nova is not None:
        restantes.append(nova)
    usos = saldo.despesas.filter(movimento_saldo=MovimentoSaldo.USO)
    reservado = usos.filter(situacao=SituacaoDespesa.PLANEJADA).aggregate(
        total=Sum("valor_original")
    )["total"]
    return motivo_de_bloqueio_da_compra(
        encerrado=saldo.encerrado,
        ha_uso_realizado=usos.filter(situacao=SituacaoDespesa.REALIZADA).exists(),
        estado_final=recompor_saldo(restantes),
        reservado=reservado or Decimal(0),
    )


def refazer_saldo(saldo: Saldo) -> None:
    """The balance is only its purchases while nothing was spent, so it is rebuilt from them."""
    estado = recompor_saldo(
        (compra.valor_original, _custo_em_brl(compra)) for compra in _compras_do_saldo(saldo)
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
