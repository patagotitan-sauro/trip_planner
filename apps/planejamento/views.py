from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.despesas.models import Despesa, SituacaoDespesa
from apps.viagens.models import EstadoViagem, Viagem
from servicos.planejamento import ordenar_por_prazo, prazo_vencido, totais_por_ano

from .totais import Orcamento, orcamento_da_viagem


@dataclass
class LinhaDaViagem:
    viagem: Viagem
    orcamento: Orcamento


def inicio(request: HttpRequest) -> HttpResponse:
    viagens = Viagem.objects.filter(estado=EstadoViagem.PLANEJAMENTO).prefetch_related("despesas")
    linhas = [
        LinhaDaViagem(viagem, orcamento_da_viagem(viagem))
        for viagem in viagens.order_by("data_inicio", "nome")
    ]

    totais = totais_por_ano((linha.viagem.data_fim, linha.orcamento.planejado) for linha in linhas)
    anos = [
        {
            "ano": ano,
            "total": total,
            "linhas": [linha for linha in linhas if linha.viagem.data_fim.year == ano],
        }
        for ano, total in totais.items()
    ]

    candidatas = Despesa.objects.filter(
        viagem__estado=EstadoViagem.PLANEJAMENTO,
        situacao=SituacaoDespesa.PLANEJADA,
        cancelavel=True,
    ).select_related("viagem")
    hoje = timezone.localdate()
    cancelaveis = ordenar_por_prazo(candidatas)
    for despesa in cancelaveis:
        despesa.vencido = prazo_vencido(despesa.data_limite_cancelamento, hoje)

    return render(request, "planejamento/inicio.html", {"anos": anos, "cancelaveis": cancelaveis})
