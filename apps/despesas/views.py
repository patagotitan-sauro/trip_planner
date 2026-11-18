from decimal import Decimal

from django.contrib import messages
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.planejamento.totais import total_gasto
from apps.viagens.cotacao import pediu_sugestao, sugerir_no_formulario
from apps.viagens.models import Viagem
from servicos.planejamento import nao_alocado_por_saldo

from .forms import DespesaForm
from .models import Despesa


def _bloqueada_por_saldo(request: HttpRequest, despesa: Despesa) -> bool:
    if not despesa.travada_por_saldo:
        return False
    messages.error(request, "Lançamentos ligados a um saldo ainda não podem ser alterados.")
    return True


def lista(request: HttpRequest, viagem_pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=viagem_pk)
    despesas = list(
        viagem.despesas.select_related("categoria", "atividade").order_by(
            F("data").asc(nulls_last=True), "id"
        )
    )
    contexto = {
        "viagem": viagem,
        "despesas": despesas,
        "total": total_gasto(viagem),
        "nao_alocado": sum(nao_alocado_por_saldo(despesas).values(), Decimal(0)),
    }
    return render(request, "despesas/lista.html", contexto)


def _formulario(
    request: HttpRequest, viagem: Viagem, despesa: Despesa | None, titulo: str
) -> HttpResponse:
    if pediu_sugestao(request):
        form = DespesaForm(
            None, instance=despesa, viagem=viagem, initial=sugerir_no_formulario(request)
        )
    else:
        dados = request.POST if request.method == "POST" else None
        form = DespesaForm(dados, instance=despesa, viagem=viagem)
    if form.is_valid():
        form.save()
        messages.success(request, "Gasto salvo.")
        return redirect("despesas:lista", viagem_pk=viagem.pk)
    return render(
        request, "despesas/formulario.html", {"form": form, "viagem": viagem, "titulo": titulo}
    )


def criar(request: HttpRequest, viagem_pk: int) -> HttpResponse:
    viagem = get_object_or_404(Viagem, pk=viagem_pk)
    return _formulario(request, viagem, None, "Novo gasto")


def editar(request: HttpRequest, viagem_pk: int, pk: int) -> HttpResponse:
    despesa = get_object_or_404(
        Despesa.objects.select_related("viagem"), pk=pk, viagem_id=viagem_pk
    )
    if _bloqueada_por_saldo(request, despesa):
        return redirect("despesas:lista", viagem_pk=viagem_pk)
    return _formulario(request, despesa.viagem, despesa, "Editar gasto")


def excluir(request: HttpRequest, viagem_pk: int, pk: int) -> HttpResponse:
    despesa = get_object_or_404(
        Despesa.objects.select_related("viagem"), pk=pk, viagem_id=viagem_pk
    )
    if _bloqueada_por_saldo(request, despesa):
        return redirect("despesas:lista", viagem_pk=viagem_pk)
    if request.method == "POST":
        despesa.delete()
        messages.success(request, "Gasto excluído.")
        return redirect("despesas:lista", viagem_pk=viagem_pk)
    return render(request, "despesas/excluir.html", {"despesa": despesa, "viagem": despesa.viagem})
