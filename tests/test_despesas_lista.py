from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, EstadoViagem, Viagem


@pytest.fixture
def viagem(db):
    return Viagem.objects.create(nome="Sul", estado=EstadoViagem.STAND_BY)


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Teste de categoria")


def _despesa(viagem, categoria, **extra):
    dados = {
        "viagem": viagem,
        "categoria": categoria,
        "descricao": "Item",
        "situacao": "realizada",
        "valor_original": Decimal("100.00"),
        "moeda": "BRL",
        "cotacao": Decimal(1),
        "valor_brl": Decimal("100.00"),
        "valor_iof": Decimal("0.00"),
    }
    dados.update(extra)
    return Despesa.objects.create(**dados)


def _html(client, viagem):
    return client.get(reverse("despesas:lista", args=[viagem.pk])).content.decode()


def test_empty_list_says_there_is_nothing_yet(logado, viagem):
    html = _html(logado, viagem)

    assert html.count("Nenhum lançamento ainda.") == 2
    assert "Custos planejados" in html
    assert "Despesas realizadas" in html


def test_planned_and_realized_are_listed_separately_with_their_own_totals(
    logado, viagem, categoria
):
    _despesa(viagem, categoria, descricao="Hotel previsto", situacao="planejada")
    _despesa(
        viagem,
        categoria,
        descricao="Jantar pago",
        valor_original=Decimal("50.00"),
        valor_brl=Decimal("50.00"),
    )

    html = _html(logado, viagem)

    previstos, realizadas = html.split("Despesas realizadas")
    assert "Hotel previsto" in previstos
    assert "Jantar pago" not in previstos
    assert "Jantar pago" in realizadas
    assert "Total: R$ 100,00" in previstos
    assert "Total: R$ 50,00" in realizadas


def test_total_includes_the_iof_and_shows_it_apart(logado, viagem, categoria):
    _despesa(
        viagem,
        categoria,
        moeda="USD",
        cotacao=Decimal("5"),
        valor_brl=Decimal("500.00"),
        valor_iof=Decimal("17.50"),
        forma_pagamento="cartao_credito",
    )

    html = _html(logado, viagem)

    assert "Total: R$ 517,50" in html
    assert "inclui R$ 17,50 de IOF" in html


def test_row_shows_original_amount_currency_rate_payment_and_category(logado, viagem, categoria):
    _despesa(
        viagem,
        categoria,
        moeda="USD",
        valor_original=Decimal("1234.50"),
        cotacao=Decimal("5.12345678"),
        valor_brl=Decimal("6325.25"),
        forma_pagamento="cartao_credito",
        data=date(2027, 3, 12),
    )

    html = _html(logado, viagem)

    assert "1.234,50 USD" in html
    assert "cotação 5,1235" in html
    assert "Cartão de crédito" in html
    assert "Teste de categoria" in html
    assert "12/03/2027" in html
    assert "6.325,25" in html


def test_brl_row_does_not_show_a_rate(logado, viagem, categoria):
    _despesa(viagem, categoria)

    assert "cotação" not in _html(logado, viagem)


def test_rows_are_sorted_by_date_with_undated_ones_last(logado, viagem, categoria):
    _despesa(viagem, categoria, descricao="Sem data")
    _despesa(viagem, categoria, descricao="Depois", data=date(2027, 3, 20))
    _despesa(viagem, categoria, descricao="Antes", data=date(2027, 3, 1))

    html = _html(logado, viagem)

    assert html.index("Antes") < html.index("Depois") < html.index("Sem data")


def test_row_shows_the_linked_activity(logado, viagem, categoria):
    atividade = AtividadeRoteiro.objects.create(viagem=viagem, dia=1, atividade="Visita ao templo")
    _despesa(viagem, categoria, atividade=atividade)

    assert "Atividade: Visita ao templo" in _html(logado, viagem)


def test_only_the_expenses_of_this_trip_are_listed(logado, viagem, categoria):
    outra = Viagem.objects.create(nome="Outra", estado=EstadoViagem.STAND_BY)
    _despesa(outra, categoria, descricao="De outra viagem")

    assert "De outra viagem" not in _html(logado, viagem)


def test_rows_link_to_edit_and_delete(logado, viagem, categoria):
    despesa = _despesa(viagem, categoria)

    html = _html(logado, viagem)

    assert reverse("despesas:editar", args=[viagem.pk, despesa.pk]) in html
    assert reverse("despesas:excluir", args=[viagem.pk, despesa.pk]) in html


def test_list_of_unknown_trip_returns_404(logado):
    assert logado.get(reverse("despesas:lista", args=[999])).status_code == 404


def test_trip_page_links_to_the_expense_list(logado, viagem):
    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert reverse("despesas:lista", args=[viagem.pk]) in html


def test_deleting_an_expense_goes_back_to_the_list(logado, viagem, categoria):
    despesa = _despesa(viagem, categoria)

    response = logado.post(reverse("despesas:excluir", args=[viagem.pk, despesa.pk]))

    assert response.url == reverse("despesas:lista", args=[viagem.pk])
