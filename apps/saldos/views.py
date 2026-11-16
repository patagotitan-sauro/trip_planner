from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.viagens.models import Viagem

from .forms import CompraDeSaldoForm


def comprar(request: HttpRequest, viagem_pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=viagem_pk)
    form = CompraDeSaldoForm(request.POST if request.method == "POST" else None, viagem=viagem)
    if form.is_valid():
        form.save()
        messages.success(request, "Compra ou carga registrada.")
        return redirect("viagens:detalhe", pk=viagem.pk)
    return render(request, "saldos/comprar.html", {"form": form, "viagem": viagem})
