import sqlite3
from datetime import time
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, EstadoViagem, Viagem

SCHEMA = """
CREATE TABLE currencies_currency (id INTEGER PRIMARY KEY, code TEXT NOT NULL);
CREATE TABLE trips_trip (
    id INTEGER PRIMARY KEY, destination TEXT NOT NULL, start_date TEXT,
    end_date TEXT NOT NULL, currency_id INTEGER NOT NULL, is_frozen INTEGER NOT NULL
);
CREATE TABLE expenses_category (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE expenses_expense (
    id INTEGER PRIMARY KEY, trip_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
    description TEXT NOT NULL, amount NUMERIC NOT NULL, status TEXT NOT NULL,
    rate_to_home NUMERIC, currency_id INTEGER
);
CREATE TABLE expenses_plannedrate (
    id INTEGER PRIMARY KEY, trip_id INTEGER NOT NULL, currency_id INTEGER NOT NULL,
    rate_to_home NUMERIC NOT NULL
);
CREATE TABLE itinerary_itineraryitem (
    id INTEGER PRIMARY KEY, trip_id INTEGER NOT NULL, date TEXT NOT NULL, time TEXT,
    activity TEXT NOT NULL, location TEXT NOT NULL, notes TEXT NOT NULL, expense_id INTEGER
);
"""

DADOS = """
INSERT INTO currencies_currency VALUES (1, 'BRL'), (2, 'ZAR');
INSERT INTO trips_trip VALUES
    (1, 'Cape Town (South Africa)', '2020-01-01', '2020-01-10', 2, 0),
    (2, 'Japão', '2099-01-01', '2099-01-10', 1, 1),
    (3, 'Manaus (Rio Negro)', '2099-02-01', '2099-02-10', 1, 0);
INSERT INTO expenses_category VALUES (1, 'Hospedagem');
INSERT INTO expenses_expense VALUES
    (1, 1, 1, 'Airbnb', 340.00, 'actual', 3.4, 2),
    (2, 1, 1, 'Museu', 2900, 'planned', NULL, 2),
    (3, 3, 1, 'Gastos', 1505.42, 'actual', 1, 1),
    (4, 3, 1, 'Taxi', 80, 'planned', NULL, NULL);
INSERT INTO expenses_plannedrate VALUES (1, 1, 2, 2.9);
INSERT INTO itinerary_itineraryitem VALUES
    (1, 1, '2020-01-02', '09:00:00', 'Hiking', 'Camps Bay', '', 1),
    (2, 3, '2099-02-02', NULL, 'Praia', 'Manaus', '', NULL);
"""


@pytest.fixture
def banco_antigo(tmp_path: Path) -> Path:
    caminho = tmp_path / "antigo.sqlite3"
    con = sqlite3.connect(caminho)
    con.executescript(SCHEMA + DADOS)
    con.close()
    return caminho


def importar(caminho: Path) -> None:
    call_command("importar_banco_antigo", str(caminho))


@pytest.mark.django_db
def test_trips_get_status_and_destination_from_old_data(banco_antigo: Path) -> None:
    importar(banco_antigo)

    assert Viagem.objects.get(nome="Cape Town (South Africa)").estado == EstadoViagem.CONCLUIDA
    assert Viagem.objects.get(nome="Japão").estado == EstadoViagem.STAND_BY
    assert Viagem.objects.get(nome="Manaus (Rio Negro)").estado == EstadoViagem.PLANEJAMENTO
    destino = Viagem.objects.get(nome="Cape Town (South Africa)").destinos.get()
    assert (destino.pais.code, destino.cidade) == ("ZA", "Cape Town")


@pytest.mark.django_db
def test_actual_expense_converts_with_its_own_rate(banco_antigo: Path) -> None:
    importar(banco_antigo)

    despesa = Despesa.objects.get(descricao="Airbnb")
    assert despesa.valor_brl == Decimal("100.00")
    assert despesa.cotacao == Decimal("0.29411765")
    assert despesa.situacao == "realizada"


@pytest.mark.django_db
def test_planned_expense_uses_shared_rate_of_its_trip(banco_antigo: Path) -> None:
    importar(banco_antigo)

    despesa = Despesa.objects.get(descricao="Museu")
    assert despesa.cotacao == Decimal("0.34482759")
    assert despesa.valor_brl == Decimal("1000.00")
    assert despesa.situacao == "planejada"


@pytest.mark.django_db
def test_expense_without_currency_uses_trip_currency(banco_antigo: Path) -> None:
    importar(banco_antigo)

    despesa = Despesa.objects.get(descricao="Taxi")
    assert despesa.moeda == "BRL"
    assert despesa.cotacao == Decimal("1")
    assert despesa.valor_brl == Decimal("80.00")


@pytest.mark.django_db
def test_itinerary_item_is_linked_to_its_old_expense(banco_antigo: Path) -> None:
    importar(banco_antigo)

    atividade = AtividadeRoteiro.objects.get(atividade="Hiking")
    assert atividade.hora == time(9, 0)
    assert Despesa.objects.get(descricao="Airbnb").atividade == atividade


@pytest.mark.django_db
def test_refuses_target_database_that_already_has_trips(banco_antigo: Path) -> None:
    Viagem.objects.create(nome="Existente", estado=EstadoViagem.STAND_BY)

    with pytest.raises(CommandError, match="já tem viagens"):
        importar(banco_antigo)


@pytest.mark.django_db
def test_unknown_destination_cancels_the_whole_import(banco_antigo: Path) -> None:
    con = sqlite3.connect(banco_antigo)
    con.execute("UPDATE trips_trip SET destination = 'Lisboa' WHERE id = 3")
    con.commit()
    con.close()

    with pytest.raises(CommandError, match="sem mapeamento"):
        importar(banco_antigo)

    assert not Viagem.objects.exists()
    assert not Categoria.objects.exists()
