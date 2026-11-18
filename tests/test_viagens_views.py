from datetime import date

from django.urls import reverse

from apps.viagens.models import Destino, EstadoViagem, Viagem


def _viagem(nome, estado=EstadoViagem.PLANEJAMENTO, fim=date(2027, 1, 10), paises=("BR",), **extra):
    # One-day trip: the start date follows the end date.
    viagem = Viagem.objects.create(nome=nome, estado=estado, data_inicio=fim, data_fim=fim, **extra)
    for pais in paises:
        Destino.objects.create(viagem=viagem, pais=pais)
    return viagem


def test_empty_list_says_there_are_no_trips(logado):
    response = logado.get(reverse("viagens:inicio"))

    assert response.status_code == 200
    assert "Nenhuma viagem para mostrar" in response.content.decode()


def test_list_shows_planning_and_completed_by_year_without_stand_by(logado):
    _viagem("Argentina", paises=("AR",))
    _viagem("Japão", EstadoViagem.STAND_BY, fim=None, paises=("JP",))
    _viagem("Manaus", EstadoViagem.CONCLUIDA, fim=date(2023, 5, 1))
    _viagem("Floripa", EstadoViagem.CONCLUIDA, fim=date(2025, 1, 10))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert "Em planejamento" in html
    assert "Japão" not in html
    assert html.index("<h3>2025: ") < html.index("<h3>2023: ")


def test_list_has_one_table_row_per_trip(logado):
    _viagem("Argentina", paises=("AR",))
    _viagem("Chile", paises=("CL",))
    _viagem("Manaus", EstadoViagem.CONCLUIDA, fim=date(2023, 5, 1))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    # Two header rows (planning and completed) plus one row per trip.
    assert html.count("<tr>") == 2 + 3


def test_list_shows_start_and_end_dates_in_separate_columns(logado):
    _viagem("Manaus", fim=date(2027, 1, 14))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert "<th>Início</th>" in html
    assert "<th>Fim</th>" in html
    assert html.count("<td>14/01/2027</td>") == 2


def test_list_shows_most_recent_trips_first(logado):
    _viagem("Floripa", fim=date(2026, 12, 27))
    _viagem("Manaus", fim=date(2027, 1, 14))
    _viagem("Gramado", EstadoViagem.CONCLUIDA, fim=date(2025, 1, 10))
    _viagem("Cabo", EstadoViagem.CONCLUIDA, fim=date(2025, 7, 20))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert html.index("Manaus") < html.index("Floripa")
    assert html.index("Cabo") < html.index("Gramado")


def test_only_trips_in_planning_have_the_edit_link(logado):
    planejada = _viagem("Argentina")
    concluida = _viagem("Manaus", EstadoViagem.CONCLUIDA, fim=date(2023, 5, 1))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert reverse("viagens:editar", args=[planejada.pk]) in html
    assert reverse("viagens:editar", args=[concluida.pk]) not in html


def test_filter_keeps_only_the_chosen_type(logado):
    _viagem("Argentina", paises=("AR",))
    _viagem("Porto Alegre", paises=("BR",))

    html = logado.get(reverse("viagens:inicio"), {"tipo": "nacional"}).content.decode()

    assert "Porto Alegre" in html
    assert "Argentina" not in html


def test_unknown_filter_value_is_ignored(logado):
    _viagem("Argentina", paises=("AR",))

    html = logado.get(reverse("viagens:inicio"), {"tipo": "outro"}).content.decode()

    assert "Argentina" in html


def test_trip_without_destination_is_listed_but_left_out_of_the_filter(logado):
    _viagem("Sem rumo", paises=())

    todas = logado.get(reverse("viagens:inicio")).content.decode()
    filtrada = logado.get(reverse("viagens:inicio"), {"tipo": "nacional"}).content.decode()

    assert "Sem rumo" in todas
    assert "Sem rumo" not in filtrada
