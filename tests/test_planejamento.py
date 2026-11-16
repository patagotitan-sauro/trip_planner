from datetime import timedelta
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
        "situacao": "planejada",
        "valor_original": Decimal(valor),
        "moeda": "BRL",
        "cotacao": Decimal(1),
        "valor_brl": Decimal(valor),
        "valor_iof": Decimal("0.00"),
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
    html = _html(logado)

    assert "Nenhuma viagem em planejamento." in html
    assert "Nenhum custo cancelável" in html


def test_planned_total_is_summed_per_year_of_the_end_date(logado, categoria):
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


def test_realized_expenses_do_not_count_as_planned(logado, categoria):
    viagem = _viagem()
    _despesa(viagem, categoria, "100.00")
    _despesa(viagem, categoria, "999.00", situacao="realizada")

    assert "R$ 100,00" in _html(logado)
    assert "999" not in _html(logado)


def test_stand_by_and_completed_trips_are_left_out(logado, categoria):
    standby = _viagem("Japão", EstadoViagem.STAND_BY)
    concluida = _viagem("Manaus", EstadoViagem.CONCLUIDA)
    _despesa(standby, categoria, "111.00")
    _despesa(concluida, categoria, "222.00")

    html = _html(logado)

    assert "Japão" not in html
    assert "Manaus" not in html
    assert "Nenhuma viagem em planejamento." in html


def test_budget_remaining_is_shown_for_trips_with_a_budget(logado, categoria):
    viagem = _viagem(orcamento=Decimal("1000.00"))
    _despesa(viagem, categoria, "350.25")

    html = _html(logado)

    assert "R$ 1.000,00" in html
    assert "R$ 649,75" in html


def test_trip_over_budget_shows_how_much(logado, categoria):
    viagem = _viagem(orcamento=Decimal("100.00"))
    _despesa(viagem, categoria, "130.00")

    assert "Estourado em R$ 30,00" in _html(logado)


def test_trip_without_budget_shows_no_remaining_value(logado, categoria):
    _despesa(_viagem(), categoria, "130.00")

    assert "Estourado" not in _html(logado)


def test_cancelable_costs_are_ordered_by_deadline_and_expired_ones_are_marked(logado, categoria):
    hoje = timezone.localdate()
    viagem = _viagem()
    _despesa(
        viagem,
        categoria,
        descricao="Hotel",
        cancelavel=True,
        data_limite_cancelamento=hoje + timedelta(days=30),
    )
    _despesa(
        viagem,
        categoria,
        descricao="Voo",
        cancelavel=True,
        data_limite_cancelamento=hoje - timedelta(days=1),
    )
    _despesa(
        viagem,
        categoria,
        descricao="Passeio",
        cancelavel=True,
        data_limite_cancelamento=hoje,
    )

    html = _html(logado)

    assert html.index("Voo") < html.index("Passeio") < html.index("Hotel")
    assert html.count("Vencido") == 1


def test_only_cancelable_costs_of_trips_in_planning_are_listed(logado, categoria):
    hoje = timezone.localdate()
    _despesa(_viagem(), categoria, descricao="Seguro")
    concluida = _viagem("Manaus", EstadoViagem.CONCLUIDA)
    _despesa(
        concluida,
        categoria,
        descricao="Barco",
        cancelavel=True,
        data_limite_cancelamento=hoje,
    )

    html = _html(logado)

    assert "Seguro" not in html
    assert "Barco" not in html
    assert "Nenhum custo cancelável" in html


def test_navigation_links_to_the_planning_page(logado):
    response = logado.get(reverse("viagens:inicio"))

    assert reverse("planejamento:inicio") in response.content.decode()
