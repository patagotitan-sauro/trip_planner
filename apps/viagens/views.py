from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from servicos.classificacao import classificar_viagem
from servicos.viagens import (
    CONCLUIDA,
    PLANEJAMENTO,
    STAND_BY,
    agrupar_roteiro,
    agrupar_viagens,
    estados_de_destino,
    nova_posicao_da_atividade,
    pode_excluir_viagem,
)

from .forms import AtividadeForm, DatasDoPlanejamentoForm, DestinoForm, ViagemForm
from .models import AtividadeRoteiro, Destino, Viagem

TIPOS = {"nacional": "Nacionais", "internacional": "Internacionais"}

ROTULOS_DA_MUDANCA = {
    (STAND_BY, PLANEJAMENTO): "Voltar ao planejamento",
    (PLANEJAMENTO, STAND_BY): "Mover para stand-by",
    (PLANEJAMENTO, CONCLUIDA): "Concluir viagem",
    (CONCLUIDA, PLANEJAMENTO): "Reabrir viagem",
}


def _tipo_da_viagem(viagem: Viagem) -> str | None:
    codigos = [destino.pais.code for destino in viagem.destinos.all()]
    # A trip without destinations has no classification and is left out of the filter (RN-02).
    return classificar_viagem(codigos) if codigos else None


def inicio(request: HttpRequest) -> HttpResponse:
    tipo = request.GET.get("tipo", "")
    if tipo not in TIPOS:
        tipo = ""

    viagens = []
    for viagem in Viagem.objects.prefetch_related("destinos"):
        viagem.tipo = _tipo_da_viagem(viagem)
        if tipo and viagem.tipo != tipo:
            continue
        viagens.append(viagem)

    contexto = {
        "grupos": agrupar_viagens(viagens),
        "total": len(viagens),
        "tipo": tipo,
        "tipos": TIPOS,
    }
    return render(request, "viagens/inicio.html", contexto)


def criar(request: HttpRequest) -> HttpResponse:
    form = ViagemForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        form.save()
        messages.success(request, "Viagem criada.")
        return redirect("viagens:inicio")
    return render(request, "viagens/formulario.html", {"form": form, "titulo": "Nova viagem"})


def editar(request: HttpRequest, pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=pk)
    form = ViagemForm(request.POST if request.method == "POST" else None, instance=viagem)
    if form.is_valid():
        form.save()
        messages.success(request, "Viagem atualizada.")
        return redirect("viagens:inicio")
    return render(
        request, "viagens/formulario.html", {"form": form, "titulo": f"Editar {viagem.nome}"}
    )


def detalhe(request: HttpRequest, pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem.objects.prefetch_related("destinos", "atividades"), pk=pk)
    form = DestinoForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        form.instance.viagem = viagem
        form.save()
        messages.success(request, "Destino adicionado.")
        return redirect("viagens:detalhe", pk=viagem.pk)
    viagem.tipo = _tipo_da_viagem(viagem)
    contexto = {
        "viagem": viagem,
        "form": form,
        "roteiro": agrupar_roteiro(list(viagem.atividades.all()), viagem.estado),
        "pode_excluir": pode_excluir_viagem(viagem.estado),
        "acoes": [
            (para, ROTULOS_DA_MUDANCA[(viagem.estado, para)])
            for para in estados_de_destino(viagem.estado)
        ],
    }
    return render(request, "viagens/detalhe.html", contexto)


def excluir(request: HttpRequest, pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=pk)
    if not pode_excluir_viagem(viagem.estado):
        messages.error(request, "Viagens concluídas ficam no histórico e não podem ser excluídas.")
        return redirect("viagens:detalhe", pk=pk)
    if request.method == "POST":
        viagem.delete()
        messages.success(request, "Viagem excluída.")
        return redirect("viagens:inicio")
    contexto = {
        "viagem": viagem,
        "destinos": viagem.destinos.count(),
        "atividades": viagem.atividades.count(),
        "despesas": viagem.despesas.count(),
    }
    return render(request, "viagens/excluir.html", contexto)


@transaction.atomic
def _aplicar_mudanca_de_estado(viagem: Viagem, para: str, datas: dict | None) -> None:
    de = viagem.estado
    referencia = viagem.data_inicio
    if para == STAND_BY:
        viagem.data_inicio = viagem.data_fim = None
    elif de == STAND_BY:
        viagem.data_inicio, viagem.data_fim = datas["data_inicio"], datas["data_fim"]
        referencia = viagem.data_inicio
    viagem.estado = para
    viagem.save()

    if STAND_BY in (de, para):
        atividades = list(viagem.atividades.all())
        for atividade in atividades:
            atividade.data, atividade.dia = nova_posicao_da_atividade(
                para, atividade.data, atividade.dia, referencia
            )
        AtividadeRoteiro.objects.bulk_update(atividades, ["data", "dia"])


def mudar_estado(request: HttpRequest, pk: int, para: str) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=pk)
    if para not in estados_de_destino(viagem.estado):
        messages.error(request, "Essa mudança de situação não é permitida.")
        return redirect("viagens:detalhe", pk=pk)

    # Leaving stand-by needs the dates back (RN-03).
    pede_datas = viagem.estado == STAND_BY
    form = None
    if pede_datas:
        form = DatasDoPlanejamentoForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and (form is None or form.is_valid()):
        _aplicar_mudanca_de_estado(viagem, para, form.cleaned_data if form else None)
        messages.success(request, "Situação da viagem atualizada.")
        return redirect("viagens:detalhe", pk=pk)

    atividades = list(viagem.atividades.all())
    if para == STAND_BY:
        posicoes = [
            nova_posicao_da_atividade(para, a.data, a.dia, viagem.data_inicio) for a in atividades
        ]
        convertidas = sum(1 for data, dia in posicoes if data is None and dia is not None)
        mantidas = sum(
            1 for a, (data, _) in zip(atividades, posicoes, strict=True) if a.data and data
        )
    else:
        convertidas = sum(1 for a in atividades if a.dia is not None) if pede_datas else 0
        mantidas = 0
    contexto = {
        "viagem": viagem,
        "para": para,
        "rotulo": ROTULOS_DA_MUDANCA[(viagem.estado, para)],
        "form": form,
        "convertidas": convertidas,
        "mantidas": mantidas,
    }
    return render(request, "viagens/mudar_estado.html", contexto)


@require_POST
def remover_destino(request: HttpRequest, pk: int, destino_pk: int) -> HttpResponse:
    destino = get_object_or_404(Destino, pk=destino_pk, viagem_id=pk)
    destino.delete()
    messages.success(request, "Destino removido.")
    return redirect("viagens:detalhe", pk=pk)


def _formulario_de_atividade(
    request: HttpRequest, viagem: Viagem, atividade: AtividadeRoteiro | None, titulo: str
) -> HttpResponse:
    form = AtividadeForm(
        request.POST if request.method == "POST" else None, instance=atividade, viagem=viagem
    )
    if form.is_valid():
        form.save()
        messages.success(request, "Atividade salva.")
        return redirect("viagens:detalhe", pk=viagem.pk)
    contexto = {"form": form, "viagem": viagem, "titulo": titulo}
    return render(request, "viagens/atividade_formulario.html", contexto)


def criar_atividade(request: HttpRequest, pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=pk)
    return _formulario_de_atividade(request, viagem, None, "Nova atividade")


def editar_atividade(request: HttpRequest, pk: int, atividade_pk: int) -> HttpResponse:
    atividade = get_object_or_404(
        AtividadeRoteiro.objects.select_related("viagem"), pk=atividade_pk, viagem_id=pk
    )
    return _formulario_de_atividade(request, atividade.viagem, atividade, "Editar atividade")


@require_POST
def remover_atividade(request: HttpRequest, pk: int, atividade_pk: int) -> HttpResponse:
    atividade = get_object_or_404(AtividadeRoteiro, pk=atividade_pk, viagem_id=pk)
    atividade.delete()
    messages.success(request, "Atividade removida.")
    return redirect("viagens:detalhe", pk=pk)
