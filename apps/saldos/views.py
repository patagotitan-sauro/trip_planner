from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.despesas.models import Despesa, MovimentoSaldo
from apps.viagens.cotacao import pediu_sugestao, sugerir_no_formulario
from apps.viagens.models import Viagem

from . import compras
from .forms import CompraDeSaldoForm


def _formulario(
    request: HttpRequest, viagem: Viagem, compra: Despesa | None = None
) -> HttpResponse:
    if pediu_sugestao(request):
        form = CompraDeSaldoForm(
            None, viagem=viagem, compra=compra, initial=sugerir_no_formulario(request)
        )
    else:
        dados = request.POST if request.method == "POST" else None
        form = CompraDeSaldoForm(dados, viagem=viagem, compra=compra)
    if form.is_valid():
        form.save()
        if compra:
            messages.success(request, "Compra ou carga alterada.")
            return redirect("despesas:lista", viagem_pk=viagem.pk)
        messages.success(request, "Compra ou carga registrada.")
        return redirect("viagens:detalhe", pk=viagem.pk)
    return render(
        request, "saldos/comprar.html", {"form": form, "viagem": viagem, "compra": compra}
    )


def _compra(viagem_pk: int, pk: int) -> Despesa:
    return get_object_or_404(
        Despesa.objects.select_related("viagem", "saldo"),
        pk=pk,
        viagem_id=viagem_pk,
        movimento_saldo=MovimentoSaldo.COMPRA,
    )


def comprar(request: HttpRequest, viagem_pk: int) -> HttpResponse:
    return _formulario(request, get_object_or_404(Viagem, pk=viagem_pk))


def editar_compra(request: HttpRequest, viagem_pk: int, pk: int) -> HttpResponse:
    compra = _compra(viagem_pk, pk)
    motivo = compras.motivo_de_bloqueio(compra)
    if motivo:
        messages.error(request, motivo)
        return redirect("despesas:lista", viagem_pk=viagem_pk)
    return _formulario(request, compra.viagem, compra)


def excluir_compra(request: HttpRequest, viagem_pk: int, pk: int) -> HttpResponse:
    compra = _compra(viagem_pk, pk)
    motivo = compras.motivo_de_bloqueio(compra)
    if motivo:
        messages.error(request, motivo)
        return redirect("despesas:lista", viagem_pk=viagem_pk)
    if request.method == "POST":
        compras.excluir_compra(compra)
        messages.success(request, "Compra ou carga excluída.")
        return redirect("despesas:lista", viagem_pk=viagem_pk)
    return render(
        request,
        "saldos/excluir_compra.html",
        {"compra": compra, "viagem": compra.viagem, "saldo": compra.saldo},
    )
