from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.saldos.models import Saldo
from apps.viagens.models import Destino, EstadoViagem, Viagem


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Teste de categoria")


def _concluida(nome, fim, pais="BR"):
    viagem = Viagem.objects.create(
        nome=nome,
        estado=EstadoViagem.CONCLUIDA,
        data_inicio=date(fim.year, 1, 1),
        data_fim=fim,
    )
    Destino.objects.create(viagem=viagem, pais=pais, cidade="Cidade")
    return viagem


def _despesa(viagem, categoria, valor, **extra):
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


def _lista(client, **params):
    return client.get(reverse("viagens:inicio"), params).content.decode()


def test_completed_trip_shows_its_total(logado, categoria):
    viagem = _concluida("Floripa", date(2025, 1, 10))
    _despesa(viagem, categoria, "100.00")
    _despesa(viagem, categoria, "50.50")

    assert "<td>R$ 150,50</td>" in _lista(logado)


def test_total_counts_the_purchase_once_and_keeps_the_closing(logado, categoria):
    viagem = _concluida("Buenos Aires", date(2025, 1, 10), pais="AR")
    saldo = Saldo.objects.create(
        viagem=viagem,
        tipo="dinheiro",
        moeda="ARS",
        valor_restante=Decimal(0),
        custo_restante=Decimal(0),
        encerrado=True,
    )
    _despesa(viagem, categoria, "500.00", movimento_saldo="compra", saldo=saldo)
    _despesa(viagem, categoria, "120.00", movimento_saldo="encerramento", saldo=saldo)

    assert "<td>R$ 500,00</td>" in _lista(logado)


def test_completed_trip_without_expenses_has_a_zero_total(logado):
    _concluida("Manaus", date(2024, 5, 1))

    assert "<td>R$ 0,00</td>" in _lista(logado)


def test_year_heading_shows_the_sum_of_its_trips_newest_year_first(logado, categoria):
    _despesa(_concluida("Floripa", date(2025, 1, 10)), categoria, "100.00")
    _despesa(_concluida("Gramado", date(2025, 7, 20)), categoria, "40.25")
    _despesa(_concluida("Manaus", date(2023, 5, 1)), categoria, "10.00")

    html = _lista(logado)

    assert "2025: R$ 140,25" in html
    assert "2023: R$ 10,00" in html
    assert html.index("2025:") < html.index("2023:")


def test_year_total_follows_the_type_filter(logado, categoria):
    _despesa(_concluida("Floripa", date(2025, 1, 10)), categoria, "100.00")
    _despesa(_concluida("Lisboa", date(2025, 6, 1), pais="PT"), categoria, "900.00")

    html = _lista(logado, tipo="nacional")

    assert "2025: R$ 100,00" in html
    assert "Lisboa" not in html


def test_planning_trip_shows_its_total_in_the_same_column(logado, categoria):
    viagem = Viagem.objects.create(
        nome="Sul",
        estado=EstadoViagem.PLANEJAMENTO,
        data_inicio=date(2027, 3, 1),
        data_fim=date(2027, 3, 10),
    )
    _despesa(viagem, categoria, "100.00")

    html = _lista(logado)

    assert "<td>R$ 100,00</td>" in html
    assert "Total gasto" in html
    assert "Custo global" not in html
    assert "Total realizado" not in html
