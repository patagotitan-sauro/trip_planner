from datetime import date

from django.urls import reverse

from apps.viagens.models import AtividadeRoteiro, EstadoViagem, Viagem


def _planejada(**extra):
    return Viagem.objects.create(
        nome="Sul",
        estado=EstadoViagem.PLANEJAMENTO,
        data_inicio=date(2027, 3, 10),
        data_fim=date(2027, 3, 20),
        **extra,
    )


def _stand_by():
    return Viagem.objects.create(nome="Japão", estado=EstadoViagem.STAND_BY)


def _url(viagem, para):
    return reverse("viagens:mudar_estado", args=[viagem.pk, para])


def _detalhe(client, viagem):
    return client.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()


def test_detail_offers_the_changes_allowed_for_each_state(logado):
    planejada = _planejada()
    stand_by = _stand_by()
    concluida = Viagem.objects.create(
        nome="Velha",
        estado=EstadoViagem.CONCLUIDA,
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 1, 5),
    )

    html_planejada = _detalhe(logado, planejada)
    html_stand_by = _detalhe(logado, stand_by)
    html_concluida = _detalhe(logado, concluida)

    assert "Mover para stand-by" in html_planejada
    assert "Concluir viagem" in html_planejada
    assert "Voltar ao planejamento" in html_stand_by
    assert "Concluir viagem" not in html_stand_by
    assert "Reabrir viagem" in html_concluida


def test_confirmation_page_does_not_change_anything(logado):
    viagem = _planejada()

    response = logado.get(_url(viagem, "concluida"))

    assert response.status_code == 200
    viagem.refresh_from_db()
    assert viagem.estado == "planejamento"


def test_complete_a_planning_trip_after_confirmation(logado):
    viagem = _planejada()

    response = logado.post(_url(viagem, "concluida"))

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert viagem.estado == "concluida"
    assert viagem.data_fim == date(2027, 3, 20)
    assert reverse("viagens:excluir", args=[viagem.pk]) not in _detalhe(logado, viagem)


def test_reopen_a_completed_trip_keeping_its_dates(logado):
    viagem = Viagem.objects.create(
        nome="Velha",
        estado=EstadoViagem.CONCLUIDA,
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 1, 5),
    )

    logado.post(_url(viagem, "planejamento"))

    viagem.refresh_from_db()
    assert (viagem.estado, viagem.data_inicio, viagem.data_fim) == (
        "planejamento",
        date(2024, 1, 1),
        date(2024, 1, 5),
    )


def test_move_to_stand_by_clears_dates_and_turns_dates_into_day_numbers(logado):
    viagem = _planejada()
    primeiro = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 3, 10), atividade="Chegada"
    )
    quarto = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 3, 13), atividade="Trilha"
    )

    response = logado.post(_url(viagem, "stand_by"))

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert (viagem.estado, viagem.data_inicio, viagem.data_fim) == ("stand_by", None, None)
    primeiro.refresh_from_db()
    quarto.refresh_from_db()
    assert (primeiro.data, primeiro.dia) == (None, 1)
    assert (quarto.data, quarto.dia) == (None, 4)


def test_activity_before_the_start_date_keeps_its_date_in_stand_by(logado):
    viagem = _planejada()
    antes = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 3, 8), atividade="Aeroporto"
    )

    logado.post(_url(viagem, "stand_by"))

    antes.refresh_from_db()
    assert (antes.data, antes.dia) == (date(2027, 3, 8), None)


def test_back_to_planning_asks_for_dates_and_turns_day_numbers_into_dates(logado):
    viagem = _stand_by()
    dia_3 = AtividadeRoteiro.objects.create(viagem=viagem, dia=3, atividade="Templo")

    response = logado.post(
        _url(viagem, "planejamento"), {"data_inicio": "2028-01-30", "data_fim": "2028-02-05"}
    )

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert (viagem.estado, viagem.data_inicio, viagem.data_fim) == (
        "planejamento",
        date(2028, 1, 30),
        date(2028, 2, 5),
    )
    dia_3.refresh_from_db()
    assert (dia_3.data, dia_3.dia) == (date(2028, 2, 1), None)


def test_back_to_planning_without_dates_shows_errors_and_changes_nothing(logado):
    viagem = _stand_by()
    atividade = AtividadeRoteiro.objects.create(viagem=viagem, dia=1, atividade="Templo")

    response = logado.post(_url(viagem, "planejamento"), {"data_inicio": "", "data_fim": ""})

    html = response.content.decode()
    assert response.status_code == 200
    assert "Informe a data de início." in html
    assert "Informe a data de fim." in html
    viagem.refresh_from_db()
    atividade.refresh_from_db()
    assert viagem.estado == "stand_by"
    assert atividade.dia == 1


def test_back_to_planning_with_end_before_start_is_rejected(logado):
    viagem = _stand_by()

    response = logado.post(
        _url(viagem, "planejamento"), {"data_inicio": "2028-02-05", "data_fim": "2028-01-30"}
    )

    assert "não pode ser anterior" in response.content.decode()
    viagem.refresh_from_db()
    assert viagem.estado == "stand_by"


def test_stand_by_and_back_restores_the_same_dates_for_activities(logado):
    viagem = _planejada()
    atividade = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 3, 12), atividade="Museu"
    )

    logado.post(_url(viagem, "stand_by"))
    logado.post(
        _url(viagem, "planejamento"), {"data_inicio": "2027-03-10", "data_fim": "2027-03-20"}
    )

    atividade.refresh_from_db()
    assert (atividade.data, atividade.dia) == (date(2027, 3, 12), None)


def test_stand_by_trip_cannot_be_completed_directly(logado):
    viagem = _stand_by()

    response = logado.post(_url(viagem, "concluida"))

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert viagem.estado == "stand_by"


def test_unknown_target_state_is_refused(logado):
    viagem = _planejada()

    response = logado.post(_url(viagem, "cancelada"))

    assert response.status_code == 302
    viagem.refresh_from_db()
    assert viagem.estado == "planejamento"


def test_confirmation_page_explains_how_the_itinerary_will_change(logado):
    viagem = _planejada()
    AtividadeRoteiro.objects.create(viagem=viagem, data=date(2027, 3, 11), atividade="A")
    AtividadeRoteiro.objects.create(viagem=viagem, data=date(2027, 3, 1), atividade="B")

    html = logado.get(_url(viagem, "stand_by")).content.decode()

    assert "1 atividade(s) do roteiro passarão da data para o número do dia" in html
    assert "1 atividade(s) são anteriores à data de início" in html


def test_state_change_of_unknown_trip_returns_404(logado):
    assert logado.get(reverse("viagens:mudar_estado", args=[999, "stand_by"])).status_code == 404
