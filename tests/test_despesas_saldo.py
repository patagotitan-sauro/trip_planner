from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa, MovimentoSaldo
from apps.saldos.models import Saldo, TipoSaldo
from apps.viagens.models import EstadoViagem, Viagem


@pytest.fixture
def viagem(db):
    return Viagem.objects.create(nome="Nova York", estado=EstadoViagem.STAND_BY)


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Passeios")


@pytest.fixture
def saldo(viagem):
    return Saldo.objects.create(
        viagem=viagem,
        tipo=TipoSaldo.DINHEIRO,
        moeda="USD",
        valor_restante=Decimal("100.00"),
        custo_restante=Decimal("505.50"),
    )


def _dados(categoria, saldo, **extra):
    dados = {
        "descricao": "Museu",
        "categoria": categoria.pk,
        "moeda": "USD",
        "valor_original": "20,00",
        "cotacao": "",
        "forma_pagamento": "",
        "saldo": saldo.pk,
    }
    dados.update(extra)
    return dados


def _criar(client, viagem, dados):
    return client.post(reverse("despesas:criar", args=[viagem.pk]), dados)


def _editar(client, despesa, dados):
    return client.post(reverse("despesas:editar", args=[despesa.viagem_id, despesa.pk]), dados)


def test_balance_question_is_not_offered_without_balances(logado, viagem):
    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert 'name="saldo"' not in html


def test_form_points_to_the_purchase_screen_when_there_is_no_balance(logado, viagem):
    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert reverse("saldos:comprar", args=[viagem.pk]) in html


def test_form_does_not_show_the_purchase_hint_when_a_balance_exists(logado, viagem, saldo):
    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert 'name="saldo"' in html
    assert reverse("saldos:comprar", args=[viagem.pk]) not in html


def test_balance_question_lists_the_open_balances(logado, viagem, saldo):
    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert 'name="saldo"' in html
    assert "Dinheiro em USD (restam 100.00 USD)" in html
    assert "Não, usar outra forma de pagamento" in html


def test_closed_and_empty_balances_are_not_offered(logado, viagem, saldo):
    Saldo.objects.filter(pk=saldo.pk).update(encerrado=True)

    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert 'name="saldo"' not in html


def test_expense_paid_with_balance_uses_the_average_cost(logado, viagem, categoria, saldo):
    resposta = _criar(logado, viagem, _dados(categoria, saldo))

    assert resposta.status_code == 302
    despesa = Despesa.objects.get()
    assert despesa.valor_brl == Decimal("101.10")
    assert despesa.forma_pagamento == "dinheiro"
    assert (despesa.saldo, despesa.movimento_saldo) == (saldo, MovimentoSaldo.USO)
    saldo.refresh_from_db()
    assert saldo.valor_restante == Decimal("80.00")
    assert saldo.custo_restante == Decimal("404.40")


def test_expense_paid_with_balance_ignores_a_typed_payment_method_and_rate(
    logado, viagem, categoria, saldo
):
    _criar(logado, viagem, _dados(categoria, saldo, forma_pagamento="cartao_credito", cotacao="9"))

    despesa = Despesa.objects.get()
    assert despesa.forma_pagamento == "dinheiro"
    assert despesa.valor_brl == Decimal("101.10")


def test_spending_the_whole_balance_takes_the_exact_remaining_cost(
    logado, viagem, categoria, saldo
):
    _criar(logado, viagem, _dados(categoria, saldo, valor_original="100,00"))

    assert Despesa.objects.get().valor_brl == Decimal("505.50")
    saldo.refresh_from_db()
    assert (saldo.valor_restante, saldo.custo_restante) == (Decimal("0.00"), Decimal("0.00"))


def test_expense_above_the_balance_is_refused(logado, viagem, categoria, saldo):
    resposta = _criar(logado, viagem, _dados(categoria, saldo, valor_original="100,01"))

    assert resposta.status_code == 200
    assert "não cobre" in resposta.content.decode()
    assert not Despesa.objects.exists()
    saldo.refresh_from_db()
    assert saldo.valor_restante == Decimal("100.00")


def test_zero_amount_cannot_be_paid_with_balance(logado, viagem, categoria, saldo):
    resposta = _criar(logado, viagem, _dados(categoria, saldo, valor_original="0"))

    assert resposta.status_code == 200
    assert not Despesa.objects.exists()


def test_balance_currency_must_match_the_expense(logado, viagem, categoria, saldo):
    resposta = _criar(logado, viagem, _dados(categoria, saldo, moeda="EUR"))

    assert resposta.status_code == 200
    assert "precisa ser na mesma moeda" in resposta.content.decode()
    assert not Despesa.objects.exists()


def test_closed_balance_cannot_pay(logado, viagem, categoria, saldo):
    # Posting the form directly: a closed balance is not even offered in the page.
    Saldo.objects.filter(pk=saldo.pk).update(encerrado=True)
    outro = Saldo.objects.create(
        viagem=viagem,
        tipo=TipoSaldo.CARTAO_PRE_PAGO,
        moeda="USD",
        valor_restante=Decimal("10"),
        custo_restante=Decimal("50"),
    )

    resposta = _criar(logado, viagem, _dados(categoria, saldo))

    assert resposta.status_code == 200
    assert not Despesa.objects.exists()
    assert outro.pk != saldo.pk


def test_expense_paid_with_balance_cannot_be_edited_or_deleted(logado, viagem, categoria, saldo):
    _criar(logado, viagem, _dados(categoria, saldo))
    despesa = Despesa.objects.get()

    editar = _editar(logado, despesa, _dados(categoria, saldo, valor_original="1,00"))
    excluir = logado.post(reverse("despesas:excluir", args=[viagem.pk, despesa.pk]))

    assert editar.status_code == 302
    assert excluir.status_code == 302
    despesa.refresh_from_db()
    assert despesa.valor_original == Decimal("20.00")


def test_expense_list_counts_what_was_paid_with_balance(logado, viagem, categoria, saldo):
    _criar(logado, viagem, _dados(categoria, saldo))

    resposta = logado.get(reverse("despesas:lista", args=[viagem.pk]))

    assert resposta.context["total"] == Decimal("101.10")
