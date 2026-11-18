from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import EstadoViagem, Viagem

URL = "/planejamento/"


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Teste de categoria")


def _viagem(nome="Sul", estado=EstadoViagem.PLANEJAMENTO, fim=None, **extra):
    hoje = timezone.localdate()
    dados = {"nome": nome, "estado": estado, "data_inicio": hoje, "data_fim": fim or hoje}
    if estado == EstadoViagem.STAND_BY:
        dados["data_inicio"] = dados["data_fim"] = None
    dados.update(extra)
    return Viagem.objects.create(**dados)


def _despesa(viagem, categoria, valor="100.00", **extra):
    dados = {
        "viagem": viagem,
        "categoria": categoria,
        "descricao": "Item",
        "valor_original": Decimal(valor),
        "moeda": "BRL",
        "cotacao": Decimal(1),
        "valor_brl": Decimal(valor),
    }
    dados.update(extra)
    return Despesa.objects.create(**dados)


def _html(client):
    return client.get(URL).content.decode()


def test_page_requires_login(client, db):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith("/contas/entrar/")


def test_page_says_there_are_no_trips_in_planning(logado):
    assert "Nenhuma viagem em planejamento." in _html(logado)


def test_total_is_summed_per_year_of_the_end_date(logado, categoria):
    hoje = timezone.localdate()
    proximo_ano = hoje.replace(year=hoje.year + 1)
    a = _viagem("Argentina", fim=hoje)
    b = _viagem("Chile", fim=hoje)
    c = _viagem("Peru", fim=proximo_ano)
    _despesa(a, categoria, "100.00")
    _despesa(b, categoria, "50.50")
    _despesa(c, categoria, "70.00")

    html = _html(logado)

    assert f"{hoje.year}: R$ 150,50" in html
    assert f"{proximo_ano.year}: R$ 70,00" in html
    assert html.index(str(proximo_ano.year)) < html.index(f"{hoje.year}:")


def test_each_trip_shows_its_own_total(logado, categoria):
    _despesa(_viagem("Argentina"), categoria, "100.00")
    _despesa(_viagem("Chile"), categoria, "50.50")

    html = _html(logado)

    assert "Argentina" in html
    assert "R$ 100,00" in html
    assert "R$ 50,50" in html


def test_stand_by_and_completed_trips_are_left_out(logado, categoria):
    standby = _viagem("Japão", EstadoViagem.STAND_BY)
    concluida = _viagem("Manaus", EstadoViagem.CONCLUIDA)
    _despesa(standby, categoria, "111.00")
    _despesa(concluida, categoria, "222.00")

    html = _html(logado)

    assert "Japão" not in html
    assert "Manaus" not in html
    assert "Nenhuma viagem em planejamento." in html


def test_page_has_no_budget_or_cancelable_sections(logado, categoria):
    _despesa(_viagem(), categoria)

    html = _html(logado)

    assert "Orçamento" not in html
    assert "cancelável" not in html.lower()


def test_navigation_links_to_the_planning_page(logado):
    response = logado.get(reverse("viagens:inicio"))

    assert reverse("planejamento:inicio") in response.content.decode()
