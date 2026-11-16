from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Despesa, MovimentoSaldo
from apps.saldos.models import Saldo, TipoSaldo
from apps.viagens.models import EstadoViagem, Viagem


@pytest.fixture
def viagem(db):
    return Viagem.objects.create(nome="Nova York", estado=EstadoViagem.STAND_BY)


def _dados(**extra):
    dados = {
        "tipo": "dinheiro",
        "moeda": "usd",
        "valor": "100,00",
        "cotacao": "5,00",
        "data": "",
    }
    dados.update(extra)
    return dados


def _comprar(client, viagem, dados):
    return client.post(reverse("saldos:comprar", args=[viagem.pk]), dados)


def test_purchase_creates_the_balance_and_a_realized_expense_with_iof(logado, viagem):
    resposta = _comprar(logado, viagem, _dados())

    assert resposta.status_code == 302
    saldo = Saldo.objects.get()
    assert (saldo.tipo, saldo.moeda) == (TipoSaldo.DINHEIRO, "USD")
    assert saldo.valor_restante == Decimal("100.00")
    assert saldo.custo_restante == Decimal("505.50")
    compra = Despesa.objects.get()
    assert compra.saldo == saldo
    assert compra.movimento_saldo == MovimentoSaldo.COMPRA
    assert compra.situacao == "realizada"
    assert compra.valor_brl == Decimal("500.00")
    assert compra.valor_iof == Decimal("5.50")
    assert compra.categoria.nome == "Outros gastos com dinheiro"


def test_prepaid_load_uses_the_prepaid_category(logado, viagem):
    _comprar(logado, viagem, _dados(tipo="cartao_pre_pago"))

    assert Despesa.objects.get().categoria.nome == "Outros gastos de cartão pré-pago"


def test_second_purchase_updates_the_average_cost(logado, viagem):
    _comprar(logado, viagem, _dados())
    _comprar(logado, viagem, _dados(cotacao="6,00"))

    saldo = Saldo.objects.get()
    assert saldo.valor_restante == Decimal("200.00")
    assert saldo.custo_restante == Decimal("1112.10")
    assert saldo.custo_medio == Decimal("5.56050000")
    assert Despesa.objects.count() == 2


def test_iof_uses_the_trip_rate(logado, viagem):
    viagem.aliquota_iof_pre_pago_dinheiro = Decimal("0.0200")
    viagem.save()

    _comprar(logado, viagem, _dados())

    assert Despesa.objects.get().valor_iof == Decimal("10.00")


def test_different_currencies_are_separate_balances(logado, viagem):
    _comprar(logado, viagem, _dados())
    _comprar(logado, viagem, _dados(moeda="EUR"))

    assert Saldo.objects.count() == 2


def test_brl_has_no_balance(logado, viagem):
    resposta = _comprar(logado, viagem, _dados(moeda="BRL"))

    assert resposta.status_code == 200
    assert "moeda estrangeira" in resposta.content.decode()
    assert not Saldo.objects.exists()


@pytest.mark.parametrize(
    "extra",
    [
        {"valor": "0"},
        {"valor": "-5"},
        {"cotacao": ""},
        {"cotacao": "0"},
        {"tipo": "pix"},
        {"moeda": "US"},
    ],
)
def test_invalid_purchase_saves_nothing(logado, viagem, extra):
    resposta = _comprar(logado, viagem, _dados(**extra))

    assert resposta.status_code == 200
    assert not Saldo.objects.exists()
    assert not Despesa.objects.exists()


def test_closed_balance_refuses_new_purchases(logado, viagem):
    _comprar(logado, viagem, _dados())
    Saldo.objects.update(encerrado=True)

    resposta = _comprar(logado, viagem, _dados())

    assert resposta.status_code == 200
    assert "encerrado" in resposta.content.decode()
    assert Saldo.objects.get().valor_restante == Decimal("100.00")


def test_trip_page_lists_the_balances(logado, viagem):
    _comprar(logado, viagem, _dados())

    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert "Dinheiro em USD" in html
    assert "505,50" in html


def test_expense_list_leaves_purchases_out_of_the_totals(logado, viagem):
    _comprar(logado, viagem, _dados())

    resposta = logado.get(reverse("despesas:lista", args=[viagem.pk]))

    realizadas = resposta.context["grupos"][1]
    assert len(realizadas["despesas"]) == 1
    assert realizadas["total"] == Decimal("0")
    assert realizadas["fora_do_total"] == 1


def test_purchase_rows_cannot_be_edited_or_deleted(logado, viagem):
    _comprar(logado, viagem, _dados())
    compra = Despesa.objects.get()

    editar = logado.get(reverse("despesas:editar", args=[viagem.pk, compra.pk]))
    excluir = logado.post(reverse("despesas:excluir", args=[viagem.pk, compra.pk]))

    assert editar.status_code == 302
    assert excluir.status_code == 302
    assert Despesa.objects.filter(pk=compra.pk).exists()


def test_purchase_form_requires_login(client, viagem):
    resposta = client.get(reverse("saldos:comprar", args=[viagem.pk]))

    assert resposta.status_code == 302
    assert reverse("contas:login") in resposta.url
