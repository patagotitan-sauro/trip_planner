from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.viagens.models import Viagem

from .forms import DespesaForm
from .models import Despesa, SituacaoDespesa


def _formulario(
    request: HttpRequest, viagem: Viagem, despesa: Despesa | None, titulo: str, initial=None
) -> HttpResponse:
    form = DespesaForm(
        request.POST if request.method == "POST" else None,
        instance=despesa,
        viagem=viagem,
        initial=initial,
    )
    if form.is_valid():
        form.save()
        messages.success(request, "Despesa salva.")
        return redirect("viagens:detalhe", pk=viagem.pk)
    return render(
        request, "despesas/formulario.html", {"form": form, "viagem": viagem, "titulo": titulo}
    )


def criar(request: HttpRequest, viagem_pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=viagem_pk)
    situacao = request.GET.get("situacao")
    initial = {"situacao": situacao} if situacao in SituacaoDespesa.values else None
    titulo = "Nova despesa" if situacao == SituacaoDespesa.REALIZADA else "Novo custo planejado"
    return _formulario(request, viagem, None, titulo, initial)


def editar(request: HttpRequest, viagem_pk: int, pk: int) -> HttpResponse:
    despesa = get_object_or_404(
        Despesa.objects.select_related("viagem"), pk=pk, viagem_id=viagem_pk
    )
    return _formulario(request, despesa.viagem, despesa, "Editar despesa")


def excluir(request: HttpRequest, viagem_pk: int, pk: int) -> HttpResponse:
    despesa = get_object_or_404(
        Despesa.objects.select_related("viagem"), pk=pk, viagem_id=viagem_pk
    )
    if request.method == "POST":
        despesa.delete()
        messages.success(request, "Despesa excluída.")
        return redirect("viagens:detalhe", pk=viagem_pk)
    return render(request, "despesas/excluir.html", {"despesa": despesa, "viagem": despesa.viagem})
