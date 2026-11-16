from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa, MovimentoSaldo
from apps.saldos.models import Saldo
from apps.viagens.models import EstadoViagem, Viagem


@pytest.fixture
def viagem(db):
    return Viagem.objects.create(nome="Nova York", estado=EstadoViagem.STAND_BY)


def _dados(**extra):
    dados = {
        "tipo": "dinheiro",
        "moeda": "USD",
        "valor": "100,00",
        "cotacao": "5,00",
        "data": "",
    }
    dados.update(extra)
    return dados


def _comprar(client, viagem, **extra):
    client.post(reverse("saldos:comprar", args=[viagem.pk]), _dados(**extra))
    return Despesa.objects.filter(movimento_saldo=MovimentoSaldo.COMPRA).latest("id")


def _url(nome, compra):
    return reverse(f"saldos:{nome}", args=[compra.viagem_id, compra.pk])


def _gastar(saldo, situacao, valor):
    categoria, _ = Categoria.objects.get_or_create(nome="Passeios")
    return Despesa.objects.create(
        viagem=saldo.viagem,
        categoria=categoria,
        descricao="Museu",
        situacao=situacao,
        valor_original=Decimal(valor),
        moeda=saldo.moeda,
        cotacao=Decimal("5.055"),
        valor_brl=Decimal("0.00"),
        forma_pagamento=saldo.tipo,
        saldo=saldo,
        movimento_saldo=MovimentoSaldo.USO,
    )


def test_editing_a_purchase_updates_it_and_rebuilds_the_balance(logado, viagem):
    compra = _comprar(logado, viagem)

    resposta = logado.post(
        _url("editar_compra", compra), _dados(valor="200,00", cotacao="6,00", data="2026-03-12")
    )

    assert resposta.status_code == 302
    compra.refresh_from_db()
    assert compra.valor_original == Decimal("200.00")
    assert compra.valor_brl == Decimal("1200.00")
    assert compra.valor_iof == Decimal("13.20")
    assert compra.data == date(2026, 3, 12)
    saldo = Saldo.objects.get()
    assert saldo.valor_restante == Decimal("200.00")
    assert saldo.custo_restante == Decimal("1213.20")


def test_editing_keeps_the_iof_rate_the_purchase_was_recorded_with(logado, viagem):
    compra = _comprar(logado, viagem)
    viagem.aliquota_iof_pre_pago_dinheiro = Decimal("0.0500")
    viagem.save()

    logado.post(_url("editar_compra", compra), _dados(valor="200,00"))

    compra.refresh_from_db()
    assert compra.taxa_iof == Decimal("0.0110")
    assert compra.valor_iof == Decimal("11.00")


def test_editing_one_of_two_purchases_recalculates_the_average_cost(logado, viagem):
    primeira = _comprar(logado, viagem)
    _comprar(logado, viagem, cotacao="6,00")

    logado.post(_url("editar_compra", primeira), _dados(cotacao="4,00"))

    saldo = Saldo.objects.get()
    assert saldo.valor_restante == Decimal("200.00")
    assert saldo.custo_restante == Decimal("1011.00")


def test_type_and_currency_cannot_be_changed_by_editing(logado, viagem):
    compra = _comprar(logado, viagem)

    logado.post(_url("editar_compra", compra), _dados(tipo="cartao_pre_pago", moeda="EUR"))

    compra.refresh_from_db()
    assert (compra.forma_pagamento, compra.moeda) == ("dinheiro", "USD")
    assert Saldo.objects.count() == 1


def test_edit_form_shows_the_current_values(logado, viagem):
    compra = _comprar(logado, viagem)

    resposta = logado.get(_url("editar_compra", compra))

    form = resposta.context["form"]
    assert form["valor"].value() == Decimal("100.00")
    assert form["cotacao"].value() == Decimal("5.00000000")
    assert "Alterar compra ou carga" in resposta.content.decode()


def test_invalid_edit_changes_nothing(logado, viagem):
    compra = _comprar(logado, viagem)

    resposta = logado.post(_url("editar_compra", compra), _dados(valor="0"))

    assert resposta.status_code == 200
    compra.refresh_from_db()
    assert compra.valor_original == Decimal("100.00")
    assert Saldo.objects.get().valor_restante == Decimal("100.00")


def test_suggest_button_fills_the_rate_without_changing_the_purchase(
    logado, viagem, provedor_de_cotacao
):
    compra = _comprar(logado, viagem)

    resposta = logado.post(
        _url("editar_compra", compra),
        {**_dados(cotacao="", data="2026-03-12"), "sugerir_cotacao": "1"},
    )

    assert resposta.context["form"]["cotacao"].value() == "5,6628"
    assert provedor_de_cotacao.chamadas == [("USD", date(2026, 3, 12))]
    compra.refresh_from_db()
    assert compra.cotacao == Decimal("5.00000000")


def test_a_purchase_with_realized_spending_cannot_be_edited(logado, viagem):
    compra = _comprar(logado, viagem)
    _gastar(Saldo.objects.get(), "realizada", "10")

    resposta = logado.post(_url("editar_compra", compra), _dados(valor="200,00"))

    assert resposta.status_code == 302
    compra.refresh_from_db()
    assert compra.valor_original == Decimal("100.00")


def test_an_edit_that_leaves_less_than_the_reserved_amount_is_refused(logado, viagem):
    compra = _comprar(logado, viagem)
    _gastar(Saldo.objects.get(), "planejada", "60")

    resposta = logado.post(_url("editar_compra", compra), _dados(valor="50,00"))

    assert resposta.status_code == 200
    assert "reservam" in resposta.content.decode()
    compra.refresh_from_db()
    assert compra.valor_original == Decimal("100.00")


def test_a_closed_balance_purchase_cannot_be_edited(logado, viagem):
    compra = _comprar(logado, viagem)
    Saldo.objects.update(encerrado=True)

    resposta = logado.get(_url("editar_compra", compra))

    assert resposta.status_code == 302


def test_delete_asks_for_confirmation_first(logado, viagem):
    compra = _comprar(logado, viagem)

    resposta = logado.get(_url("excluir_compra", compra))

    assert resposta.status_code == 200
    assert Despesa.objects.filter(pk=compra.pk).exists()


def test_deleting_the_only_purchase_removes_the_balance(logado, viagem):
    compra = _comprar(logado, viagem)

    resposta = logado.post(_url("excluir_compra", compra))

    assert resposta.status_code == 302
    assert not Despesa.objects.exists()
    assert not Saldo.objects.exists()


def test_deleting_one_of_two_purchases_rebuilds_the_balance(logado, viagem):
    _comprar(logado, viagem)
    segunda = _comprar(logado, viagem, cotacao="6,00")

    logado.post(_url("excluir_compra", segunda))

    saldo = Saldo.objects.get()
    assert saldo.valor_restante == Decimal("100.00")
    assert saldo.custo_restante == Decimal("505.50")
    assert Despesa.objects.count() == 1


def test_a_purchase_with_realized_spending_cannot_be_deleted(logado, viagem):
    compra = _comprar(logado, viagem)
    _gastar(Saldo.objects.get(), "realizada", "10")

    resposta = logado.post(_url("excluir_compra", compra))

    assert resposta.status_code == 302
    assert Despesa.objects.filter(pk=compra.pk).exists()


def test_deleting_a_purchase_that_a_reservation_depends_on_is_refused(logado, viagem):
    compra = _comprar(logado, viagem)
    _gastar(Saldo.objects.get(), "planejada", "30")

    resposta = logado.post(_url("excluir_compra", compra))

    assert resposta.status_code == 302
    assert Despesa.objects.filter(pk=compra.pk).exists()
    assert Saldo.objects.get().valor_restante == Decimal("100.00")


def test_only_purchases_use_these_screens(logado, viagem):
    _comprar(logado, viagem)
    uso = _gastar(Saldo.objects.get(), "planejada", "10")

    assert logado.get(_url("editar_compra", uso)).status_code == 404
    assert logado.post(_url("excluir_compra", uso)).status_code == 404


def test_purchase_of_another_trip_is_not_found(logado, viagem):
    compra = _comprar(logado, viagem)
    outra = Viagem.objects.create(nome="Lima", estado=EstadoViagem.STAND_BY)

    resposta = logado.get(reverse("saldos:editar_compra", args=[outra.pk, compra.pk]))

    assert resposta.status_code == 404


def test_expense_list_links_purchase_rows_to_the_purchase_screens(logado, viagem):
    compra = _comprar(logado, viagem)

    html = logado.get(reverse("despesas:lista", args=[viagem.pk])).content.decode()

    assert _url("editar_compra", compra) in html
    assert _url("excluir_compra", compra) in html


def test_purchase_screens_require_login(client, viagem, logado):
    compra = _comprar(logado, viagem)
    client.logout()

    for nome in ("editar_compra", "excluir_compra"):
        resposta = client.post(_url(nome, compra))
        assert resposta.status_code == 302
        assert reverse("contas:login") in resposta.url
    assert Despesa.objects.filter(pk=compra.pk).exists()
