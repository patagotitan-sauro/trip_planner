from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from servicos.classificacao import classificar_viagem
from servicos.viagens import agrupar_viagens

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
