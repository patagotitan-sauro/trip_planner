from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from servicos.classificacao import classificar_viagem
from servicos.viagens import agrupar_viagens

from .forms import ViagemForm
from .models import Viagem

TIPOS = {"nacional": "Nacionais", "internacional": "Internacionais"}


def inicio(request: HttpRequest) -> HttpResponse:
    tipo = request.GET.get("tipo", "")
    if tipo not in TIPOS:
        tipo = ""

    viagens = []
    for viagem in Viagem.objects.prefetch_related("destinos"):
        codigos = [destino.pais.code for destino in viagem.destinos.all()]
        # A trip without destinations has no classification and is left out of the filter (RN-02).
        viagem.tipo = classificar_viagem(codigos) if codigos else None
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
