from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import EstadoViagem, Viagem


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Teste de categoria")


def _viagem(estado=EstadoViagem.PLANEJAMENTO, **extra):
    dados = {"nome": "Sul", "estado": estado, "orcamento": Decimal("1000.00")}
    if estado != EstadoViagem.STAND_BY:
        dados.update(data_inicio=date(2027, 3, 1), data_fim=date(2027, 3, 10))
    dados.update(extra)
    return Viagem.objects.create(**dados)


def _despesa(viagem, categoria, valor, situacao="planejada"):
    return Despesa.objects.create(
        viagem=viagem,
        categoria=categoria,
        descricao="Item",
        situacao=situacao,
        valor_original=Decimal(valor),
        moeda="BRL",
        cotacao=Decimal(1),
        valor_brl=Decimal(valor),
    )


def _detalhe(client, viagem):
    return client.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()


def _lista(client):
    return client.get(reverse("viagens:inicio")).content.decode()


def test_detail_shows_planned_total_and_remaining_budget(logado, categoria):
    viagem = _viagem()
    _despesa(viagem, categoria, "350.25")

    html = _detalhe(logado, viagem)

    assert "Planejado: R$ 350,25" in html
    assert "Restante: R$ 649,75" in html


def test_detail_shows_how_much_the_plan_exceeds_the_budget(logado, categoria):
    viagem = _viagem(orcamento=Decimal("100.00"))
    _despesa(viagem, categoria, "130.00")

    html = _detalhe(logado, viagem)

    assert "Estourado em R$ 30,00" in html
    assert "Restante" not in html


def test_remaining_budget_ignores_realized_expenses(logado, categoria):
    viagem = _viagem()
    _despesa(viagem, categoria, "100.00")
    _despesa(viagem, categoria, "400.00", situacao="realizada")

    assert "Restante: R$ 900,00" in _detalhe(logado, viagem)


def test_trip_without_budget_shows_no_remaining_value(logado, categoria):
    viagem = _viagem(orcamento=None)
    _despesa(viagem, categoria, "100.00")

    html = _detalhe(logado, viagem)

    assert "Restante" not in html
    assert "Planejado:" not in html


def test_stand_by_trip_with_budget_shows_remaining_value(logado, categoria):
    viagem = _viagem(EstadoViagem.STAND_BY)
    _despesa(viagem, categoria, "200.00")

    assert "Restante: R$ 800,00" in _detalhe(logado, viagem)


def test_completed_trip_does_not_show_remaining_value(logado, categoria):
    viagem = _viagem(EstadoViagem.CONCLUIDA)
    _despesa(viagem, categoria, "200.00")

    assert "Restante" not in _detalhe(logado, viagem)


def test_trip_card_shows_remaining_budget(logado, categoria):
    viagem = _viagem()
    _despesa(viagem, categoria, "250.00")

    html = _lista(logado)

    assert "Orçamento: R$ 1.000,00" in html
    assert "Restante: R$ 750,00" in html


def test_completed_trip_card_shows_only_the_budget(logado):
    _viagem(EstadoViagem.CONCLUIDA)

    html = _lista(logado)

    assert "Orçamento: R$ 1.000,00" in html
    assert "Restante" not in html
