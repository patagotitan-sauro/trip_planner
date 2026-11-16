from dataclasses import dataclass
from decimal import Decimal

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.despesas.models import Despesa, SituacaoDespesa
from apps.viagens.models import EstadoViagem, Viagem
from servicos.planejamento import ordenar_por_prazo, prazo_vencido, totais_por_ano, valor_restante

from .totais import total_planejado


@dataclass
class LinhaDaViagem:
    viagem: Viagem
    planejado: Decimal
    restante: Decimal | None

    @property
    def excesso(self) -> Decimal | None:
        return -self.restante if self.restante is not None and self.restante < 0 else None


def inicio(request: HttpRequest) -> HttpResponse:
    viagens = Viagem.objects.filter(estado=EstadoViagem.PLANEJAMENTO).prefetch_related("despesas")
    linhas = []
    for viagem in viagens.order_by("data_inicio", "nome"):
        planejado = total_planejado(viagem)
        linhas.append(LinhaDaViagem(viagem, planejado, valor_restante(viagem.orcamento, planejado)))

    totais = totais_por_ano((linha.viagem.data_fim, linha.planejado) for linha in linhas)
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
