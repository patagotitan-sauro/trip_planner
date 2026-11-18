from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.viagens.models import EstadoViagem, Viagem
from servicos.planejamento import totais_por_ano

from .totais import total_gasto


def inicio(request: HttpRequest) -> HttpResponse:
    viagens = Viagem.objects.filter(estado=EstadoViagem.PLANEJAMENTO).prefetch_related("despesas")
    linhas = [
        {"viagem": viagem, "total": total_gasto(viagem)}
        for viagem in viagens.order_by("data_inicio", "nome")
    ]

    totais = totais_por_ano((linha["viagem"].data_fim, linha["total"]) for linha in linhas)
    anos = [
        {
            "ano": ano,
            "total": total,
            "linhas": [linha for linha in linhas if linha["viagem"].data_fim.year == ano],
        }
        for ano, total in totais.items()
    ]
    return render(request, "planejamento/inicio.html", {"anos": anos})
