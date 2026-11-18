from decimal import Decimal

from django.db import transaction

from apps.despesas.models import Categoria, Despesa, MovimentoSaldo
from apps.viagens.models import Viagem
from servicos.saldos import categoria_de_encerramento

from .models import Saldo


def saldos_a_encerrar(viagem: Viagem) -> list[Saldo]:
    """Open balances of the trip that still have something left (RF-16)."""
    return list(
        viagem.saldos.filter(encerrado=False, valor_restante__gt=0).order_by("moeda", "tipo")
    )


@transaction.atomic
def encerrar_saldos(viagem: Viagem) -> list[Despesa]:
    """RN-14: posts what is left of each balance as an "Outros gastos" expense and closes it.

    The leftover keeps the BRL cost already paid, so the cost is not counted again.
    """
    lancamentos = []
    for saldo in saldos_a_encerrar(viagem):
        categoria, _ = Categoria.objects.get_or_create(nome=categoria_de_encerramento(saldo.tipo))
        lancamentos.append(
            Despesa.objects.create(
                viagem=viagem,
                categoria=categoria,
                descricao=f"Saldo não usado: {saldo}",
                data=viagem.data_fim,
                valor_original=saldo.valor_restante,
                moeda=saldo.moeda,
                cotacao=saldo.custo_medio,
                valor_brl=saldo.custo_restante,
                forma_pagamento=saldo.tipo,
                saldo=saldo,
                movimento_saldo=MovimentoSaldo.ENCERRAMENTO,
            )
        )
        saldo.valor_restante = saldo.custo_restante = Decimal(0)
        saldo.encerrado = True
        saldo.save(update_fields=["valor_restante", "custo_restante", "encerrado"])
    # Balances fully spent have nothing to post, but they close with the trip too.
    viagem.saldos.filter(encerrado=False).update(encerrado=True)
    return lancamentos
