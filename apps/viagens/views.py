from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from servicos.classificacao import classificar_viagem
from servicos.viagens import agrupar_roteiro, agrupar_viagens, pode_excluir_viagem

from .forms import AtividadeForm, DestinoForm, ViagemForm
from .models import AtividadeRoteiro, Destino, Viagem

TIPOS = {"nacional": "Nacionais", "internacional": "Internacionais"}


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
