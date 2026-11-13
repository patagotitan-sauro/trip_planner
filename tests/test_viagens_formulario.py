from datetime import date
from decimal import Decimal

from django.urls import reverse

from apps.viagens.models import EstadoViagem, Viagem

DADOS = {
    "nome": "Argentina",
    "estado": "planejamento",
    "pais": "AR",
    "cidade": "Buenos Aires",
    "data_inicio": "2027-02-01",
    "data_fim": "2027-02-10",
    "orcamento": "",
}


def test_create_form_offers_only_planning_and_stand_by(logado):
    html = logado.get(reverse("viagens:criar")).content.decode()

    assert 'value="concluida"' not in html
    assert 'value="planejamento"' in html
    assert 'value="stand_by"' in html


def test_create_form_asks_for_country_and_city_with_brasil_as_default(logado):
    html = logado.get(reverse("viagens:criar")).content.decode()

    assert 'name="pais"' in html
    assert 'name="cidade"' in html
    assert '<option value="BR" selected>' in html


def test_create_trip_also_creates_its_first_destination(logado):
    logado.post(reverse("viagens:criar"), DADOS)

    destino = Viagem.objects.get().destinos.get()
    assert (destino.pais.code, destino.cidade) == ("AR", "Buenos Aires")


def test_create_trip_without_city_is_rejected_and_saves_nothing(logado):
    response = logado.post(reverse("viagens:criar"), {**DADOS, "cidade": ""})

    assert "Informe a cidade." in response.content.decode()
    assert not Viagem.objects.exists()


def test_create_trip_without_country_is_rejected_and_saves_nothing(logado):
    response = logado.post(reverse("viagens:criar"), {**DADOS, "pais": ""})

    assert response.status_code == 200
    assert not Viagem.objects.exists()


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
    assert 'name="pais"' not in html
    assert 'name="cidade"' not in html
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


def test_create_form_shows_the_default_iof_rates_as_percentages(logado):
    html = logado.get(reverse("viagens:criar")).content.decode()

    assert 'name="aliquota_iof_credito"' in html
    assert 'value="3,50"' in html
    assert 'value="1,10"' in html


def test_create_trip_without_rates_uses_the_defaults(logado):
    logado.post(reverse("viagens:criar"), DADOS)

    viagem = Viagem.objects.get()
    assert viagem.aliquota_iof_credito == Decimal("0.0350")
    assert viagem.aliquota_iof_pre_pago_dinheiro == Decimal("0.0110")


def test_create_trip_with_custom_iof_rates_stores_fractions(logado):
    dados = {**DADOS, "aliquota_iof_credito": "4,5", "aliquota_iof_pre_pago_dinheiro": "0"}

    logado.post(reverse("viagens:criar"), dados)

    viagem = Viagem.objects.get()
    assert viagem.aliquota_iof_credito == Decimal("0.0450")
    assert viagem.aliquota_iof_pre_pago_dinheiro == Decimal("0")


def test_iof_rate_accepts_two_decimal_places_and_one_hundred_percent(logado):
    dados = {**DADOS, "aliquota_iof_credito": "3,55", "aliquota_iof_pre_pago_dinheiro": "100"}

    logado.post(reverse("viagens:criar"), dados)

    viagem = Viagem.objects.get()
    assert viagem.aliquota_iof_credito == Decimal("0.0355")
    assert viagem.aliquota_iof_pre_pago_dinheiro == Decimal("1")


def test_invalid_iof_rates_are_rejected_with_a_clear_message(logado):
    for invalido in ("101", "-1", "3,555", "abc"):
        response = logado.post(
            reverse("viagens:criar"), {**DADOS, "aliquota_iof_credito": invalido}
        )

        assert "percentual entre 0 e 100" in response.content.decode(), invalido
    assert not Viagem.objects.exists()


def test_edit_shows_and_changes_the_trip_iof_rates(logado):
    viagem = Viagem.objects.create(
        nome="Sul",
        estado=EstadoViagem.STAND_BY,
        aliquota_iof_credito=Decimal("0.0400"),
    )
    url = reverse("viagens:editar", args=[viagem.pk])

    assert 'value="4,00"' in logado.get(url).content.decode()

    logado.post(
        url, {"nome": "Sul", "aliquota_iof_credito": "5", "aliquota_iof_pre_pago_dinheiro": ""}
    )

    viagem.refresh_from_db()
    assert viagem.aliquota_iof_credito == Decimal("0.0500")
    assert viagem.aliquota_iof_pre_pago_dinheiro == Decimal("0.0110")


def test_editing_without_the_rate_fields_keeps_the_current_rates(logado):
    viagem = Viagem.objects.create(
        nome="Sul",
        estado=EstadoViagem.STAND_BY,
        aliquota_iof_credito=Decimal("0.0400"),
    )

    logado.post(reverse("viagens:editar", args=[viagem.pk]), {"nome": "Sul 2"})

    viagem.refresh_from_db()
    assert viagem.aliquota_iof_credito == Decimal("0.0400")


def test_detail_shows_the_iof_rates_in_percent(logado):
    viagem = Viagem.objects.create(
        nome="Sul", estado=EstadoViagem.STAND_BY, aliquota_iof_credito=Decimal("0.0400")
    )

    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert "cartão de crédito 4,00%" in html
    assert "cartão pré-pago e dinheiro 1,10%" in html
