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


def test_list_shows_the_three_groups_with_completed_ones_by_year(logado):
    _viagem("Argentina", paises=("AR",))
    _viagem("Japão", EstadoViagem.STAND_BY, fim=None, paises=("JP",))
    _viagem("Manaus", EstadoViagem.CONCLUIDA, fim=date(2023, 5, 1))
    _viagem("Floripa", EstadoViagem.CONCLUIDA, fim=date(2025, 1, 10))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert "Em planejamento" in html
    assert "Stand-by" in html
    assert html.index("<h3>2025</h3>") < html.index("<h3>2023</h3>")
    assert "Sem datas" in html


def test_list_labels_trips_as_national_or_international(logado):
    _viagem("Argentina", paises=("AR",))
    _viagem("Porto Alegre", paises=("BR",))
    _viagem("Mista", paises=("BR", "UY"))

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert html.count("<mark>Internacional</mark>") == 2
    assert html.count("<mark>Nacional</mark>") == 1


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

    assert "Sem destino" in todas
    assert "Sem rumo" not in filtrada


def test_budget_is_shown_in_reais_when_set(logado):
    _viagem("Com orçamento", orcamento="12500.50")

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert "Orçamento: R$ 12.500,50" in html


def test_destinations_show_city_and_country_name(logado):
    viagem = _viagem("Sul", paises=("BR",))
    Destino.objects.create(viagem=viagem, pais="AR", cidade="Buenos Aires")

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert "Buenos Aires, Argentina" in html
    assert "Brasil" in html
