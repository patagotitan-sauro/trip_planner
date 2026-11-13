from datetime import date
from decimal import Decimal

from django.urls import reverse

from apps.viagens.models import EstadoViagem, Viagem

DADOS = {
    "nome": "Argentina",
    "estado": "planejamento",
    "data_inicio": "2027-02-01",
    "data_fim": "2027-02-10",
    "orcamento": "",
}


def test_create_form_offers_only_planning_and_stand_by(logado):
    html = logado.get(reverse("viagens:criar")).content.decode()

    assert 'value="concluida"' not in html
    assert 'value="planejamento"' in html
    assert 'value="stand_by"' in html


def test_create_planning_trip_with_dates_and_no_budget(logado):
    response = logado.post(reverse("viagens:criar"), DADOS)

    assert response.status_code == 302
    viagem = Viagem.objects.get()
    assert (viagem.nome, viagem.estado, viagem.orcamento) == ("Argentina", "planejamento", None)
    assert viagem.data_fim == date(2027, 2, 10)


def test_create_stand_by_trip_without_dates(logado):
    dados = {**DADOS, "estado": "stand_by", "data_inicio": "", "data_fim": ""}

    logado.post(reverse("viagens:criar"), dados)

    viagem = Viagem.objects.get()
    assert (viagem.estado, viagem.data_inicio, viagem.data_fim) == ("stand_by", None, None)


def test_planning_trip_without_dates_shows_errors_and_is_not_saved(logado):
    dados = {**DADOS, "data_inicio": "", "data_fim": ""}

    response = logado.post(reverse("viagens:criar"), dados)

    html = response.content.decode()
    assert response.status_code == 200
    assert "Informe a data de início." in html
    assert "Informe a data de fim." in html
    assert not Viagem.objects.exists()


def test_end_date_before_start_date_is_rejected(logado):
    dados = {**DADOS, "data_inicio": "2027-02-10", "data_fim": "2027-02-01"}

    response = logado.post(reverse("viagens:criar"), dados)

    assert "não pode ser anterior" in response.content.decode()
    assert not Viagem.objects.exists()


def test_budget_accepts_brazilian_decimal_comma(logado):
    logado.post(reverse("viagens:criar"), {**DADOS, "orcamento": "12500,50"})

    assert Viagem.objects.get().orcamento == Decimal("12500.50")


def test_negative_budget_is_rejected(logado):
    response = logado.post(reverse("viagens:criar"), {**DADOS, "orcamento": "-1"})

    assert "O orçamento não pode ser negativo." in response.content.decode()
    assert not Viagem.objects.exists()


def test_blank_name_is_rejected(logado):
    response = logado.post(reverse("viagens:criar"), {**DADOS, "nome": ""})

    assert response.status_code == 200
    assert not Viagem.objects.exists()


def test_edit_changes_the_trip_and_keeps_its_state(logado):
    viagem = Viagem.objects.create(
        nome="Velho",
        estado=EstadoViagem.CONCLUIDA,
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 1, 5),
    )
    dados = {"nome": "Novo", "data_inicio": "2024-01-01", "data_fim": "2024-01-06", "orcamento": ""}

    response = logado.post(reverse("viagens:editar", args=[viagem.pk]), dados)

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert (viagem.nome, viagem.estado, viagem.data_fim) == (
        "Novo",
        "concluida",
        date(2024, 1, 6),
    )


def test_edit_form_has_no_state_field_and_shows_current_values(logado):
    viagem = Viagem.objects.create(nome="Japão", estado=EstadoViagem.STAND_BY)

    html = logado.get(reverse("viagens:editar", args=[viagem.pk])).content.decode()

    assert 'name="estado"' not in html
    assert 'value="Japão"' in html


def test_edit_stand_by_trip_does_not_require_dates(logado):
    viagem = Viagem.objects.create(nome="Japão", estado=EstadoViagem.STAND_BY)

    response = logado.post(reverse("viagens:editar", args=[viagem.pk]), {"nome": "Japão 2"})

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert viagem.nome == "Japão 2"


def test_edit_unknown_trip_returns_404(logado):
    assert logado.get(reverse("viagens:editar", args=[999])).status_code == 404


def test_list_links_to_create_and_edit(logado):
    viagem = Viagem.objects.create(nome="Japão", estado=EstadoViagem.STAND_BY)

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert reverse("viagens:criar") in html
    assert reverse("viagens:editar", args=[viagem.pk]) in html
