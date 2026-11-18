from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.saldos.models import Saldo
from apps.viagens.models import Destino, EstadoViagem, Viagem

URL_STAND_BY = "/viagens/stand-by/"


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Teste de categoria")


def _viagem(nome, estado=EstadoViagem.PLANEJAMENTO, pais="BR"):
    datas = {"data_inicio": date(2027, 3, 1), "data_fim": date(2027, 3, 10)}
    if estado == EstadoViagem.STAND_BY:
        datas = {"data_inicio": None, "data_fim": None}
    viagem = Viagem.objects.create(nome=nome, estado=estado, **datas)
    Destino.objects.create(viagem=viagem, pais=pais)
    return viagem


def _despesa(viagem, categoria, valor, situacao="realizada", **extra):
    dados = {
        "viagem": viagem,
        "categoria": categoria,
        "descricao": "Item",
        "situacao": situacao,
        "valor_original": Decimal(valor),
        "moeda": "BRL",
        "cotacao": Decimal(1),
        "valor_brl": Decimal(valor),
        "valor_iof": Decimal("0.00"),
    }
    dados.update(extra)
    return Despesa.objects.create(**dados)


def _html(client, url, **params):
    return client.get(url, params).content.decode()


def test_stand_by_page_requires_login(client, db):
    response = client.get(URL_STAND_BY)

    assert response.status_code == 302
    assert response.url.startswith("/contas/entrar/")


def test_stand_by_page_lists_only_stand_by_trips(logado):
    _viagem("Japão", EstadoViagem.STAND_BY, pais="JP")
    _viagem("Argentina", pais="AR")
    _viagem("Manaus", EstadoViagem.CONCLUIDA)

    html = _html(logado, reverse("viagens:stand_by"))

    assert "Japão" in html
    assert "Argentina" not in html
    assert "Manaus" not in html
    assert "&mdash;" in html


def test_stand_by_page_says_when_there_are_none(logado):
    assert "Nenhuma viagem em stand-by para mostrar." in _html(logado, URL_STAND_BY)


def test_stand_by_page_keeps_the_type_filter_and_has_no_edit_link(logado):
    japao = _viagem("Japão", EstadoViagem.STAND_BY, pais="JP")
    _viagem("Bonito", EstadoViagem.STAND_BY, pais="BR")

    html = _html(logado, URL_STAND_BY, tipo="internacional")

    assert "Japão" in html
    assert "Bonito" not in html
    assert reverse("viagens:detalhe", args=[japao.pk]) in html
    assert reverse("viagens:editar", args=[japao.pk]) not in html


def test_first_page_links_to_stand_by_trips_and_keeps_the_filter(logado):
    html = _html(logado, reverse("viagens:inicio"), tipo="nacional")

    assert "Viagens em stand-by" in html
    assert f'href="{URL_STAND_BY}?tipo=nacional"' in html


def test_global_cost_is_realized_plus_planned(logado, categoria):
    viagem = _viagem("Sul")
    _despesa(viagem, categoria, "100.00")
    _despesa(viagem, categoria, "50.50", situacao="planejada")
    _despesa(viagem, categoria, "10.00", valor_iof=Decimal("0.25"))

    assert "<td>R$ 160,75</td>" in _html(logado, reverse("viagens:inicio"))


def test_global_cost_does_not_count_the_balance_purchase_twice(logado, categoria):
    viagem = _viagem("Buenos Aires", pais="AR")
    saldo = Saldo.objects.create(
        viagem=viagem,
        tipo="dinheiro",
        moeda="ARS",
        valor_restante=Decimal("420.00"),
        custo_restante=Decimal("420.00"),
    )
    _despesa(viagem, categoria, "500.00", movimento_saldo="compra", saldo=saldo)
    _despesa(viagem, categoria, "80.00", movimento_saldo="uso", saldo=saldo)
    _despesa(viagem, categoria, "40.00", situacao="planejada")

    assert "<td>R$ 120,00</td>" in _html(logado, reverse("viagens:inicio"))


def test_stand_by_trip_shows_its_global_cost(logado, categoria):
    viagem = _viagem("Japão", EstadoViagem.STAND_BY, pais="JP")
    _despesa(viagem, categoria, "900.00", situacao="planejada")

    assert "<td>R$ 900,00</td>" in _html(logado, URL_STAND_BY)


def test_year_heading_keeps_the_realized_total_only(logado, categoria):
    viagem = Viagem.objects.create(
        nome="Floripa",
        estado=EstadoViagem.CONCLUIDA,
        data_inicio=date(2025, 1, 1),
        data_fim=date(2025, 1, 10),
    )
    _despesa(viagem, categoria, "100.00")
    _despesa(viagem, categoria, "900.00", situacao="planejada")

    html = _html(logado, reverse("viagens:inicio"))

    assert "2025: R$ 100,00" in html
    assert "Custo global" not in html
